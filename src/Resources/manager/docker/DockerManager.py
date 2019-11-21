from datetime import datetime
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool

import docker
import logging
from requests.exceptions import ConnectionError as RequestsConnectionError
from terminaltables import DoubleTable

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from ... import utils
from ...auth.PrivilegeHandler import PrivilegeHandler
from ...exceptions import DockerDaemonConnectionError
from ...foundation.manager.IManager import IManager
from ...model.Link import BRIDGE_LINK_NAME


def pywin_import_stub():
    """
    Stub module of pywintypes for Unix systems (so it won't raise any `module not found` exception).
    """
    import types
    pywintypes = types.ModuleType("pywintypes")
    pywintypes.error = RequestsConnectionError
    return pywintypes


def pywin_import_win():
    import pywintypes
    return pywintypes


def privileged(method):
    """
    Decorator function to execute Docker daemon with proper privileges.
    They are then dropped when method is executed.
    """
    def exec_with_privileges(*args, **kw):
        utils.exec_by_platform(PrivilegeHandler.get_instance().raise_privileges, lambda: None, lambda: None)
        result = method(*args, **kw)
        utils.exec_by_platform(PrivilegeHandler.get_instance().drop_privileges, lambda: None, lambda: None)

        return result

    return exec_with_privileges


def check_docker_status(method):
    """
    Decorator function to check if Docker daemon is running properly.
    """
    pywintypes = utils.exec_by_platform(pywin_import_stub, pywin_import_win, pywin_import_stub)

    @privileged
    def check_docker(*args, **kw):
        # Call the constructor first
        method(*args, **kw)

        # Client is initialized after constructor call
        client = args[0].client

        # Try to ping Docker, to see if it's running and raise an exception on failure
        try:
            client.ping()
        except RequestsConnectionError as e:
            raise DockerDaemonConnectionError("Can not connect to Docker Daemon. %s" % str(e))
        except pywintypes.error as e:
            raise DockerDaemonConnectionError("Can not connect to Docker Daemon. %s" % str(e))

    return check_docker


class DockerManager(IManager):
    __slots__ = ['docker_image', 'docker_machine', 'docker_link', 'client']

    @check_docker_status
    def __init__(self):
        self.client = docker.from_env()

        self.docker_image = DockerImage(self.client)

        self.docker_machine = DockerMachine(self.client, self.docker_image)
        self.docker_link = DockerLink(self.client, self.docker_image)

    @privileged
    def deploy_lab(self, lab):
        # Deploy all lab links.
        for (_, link) in lab.links.items():
            logging.info("Deploying link %s." % link.name)
            self.docker_link.deploy(link)

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.docker_link.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.api_object = docker_bridge

        # Deploy all lab machines.
        # If there is no lab.dep file, machines can be deployed using multithreading.
        # If not, they're started sequentially
        if not lab.has_dependencies:
            cpus = cpu_count()
            machines_pool = Pool(cpus)

            machines = lab.machines.items()
            items = [machines] if len(machines) < cpus else \
                                  utils.list_chunks(machines, cpus)

            for chunk in items:
                machines_pool.map(func=self._deploy_and_start_machine, iterable=chunk)
        else:
            for item in lab.machines.items():
                self._deploy_and_start_machine(item)

    def _deploy_and_start_machine(self, machine_item):
        (_, machine) = machine_item

        self.docker_machine.deploy(machine)

        logging.info("Starting machine %s." % machine.name)
        self.docker_machine.start(machine)

    @privileged
    def update_lab(self, lab_diff):
        # Deploy new links (if present)
        for (_, link) in lab_diff.links.items():
            self.docker_link.deploy(link)

        # Update lab machines.
        for (_, machine) in lab_diff.machines.items():
            self.docker_machine.update(machine)

    @privileged
    def undeploy_lab(self, lab_hash, selected_machines=None):
        self.docker_machine.undeploy(lab_hash,
                                     selected_machines=selected_machines
                                     )
        self.docker_link.undeploy(lab_hash)

    @privileged
    def wipe(self, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        self.docker_machine.wipe(user=user_name)
        self.docker_link.wipe(user=user_name)

    @privileged
    def connect_tty(self, lab_hash, machine_name, shell, logs=False):
        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    shell=shell,
                                    logs=logs
                                    )

    @privileged
    def exec(self, machine, command):
        return self.docker_machine.exec(machine.api_object,
                                        command=command
                                        )

    @privileged
    def copy_files(self, machine, path, tar_data):
        self.docker_machine.copy_files(machine.api_object,
                                       path=path,
                                       tar_data=tar_data
                                       )

    @privileged
    def get_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        machines = self.docker_machine.get_machines_by_filters(lab_hash=lab_hash,
                                                               machine_name=machine_name,
                                                               user=user_name
                                                               )

        if not machines:
            if not lab_hash:
                raise Exception("No machines running.")
            else:
                raise Exception("Lab is not started.")

        machines = sorted(machines, key=lambda x: x.name)

        machine_streams = {}

        for machine in machines:
            machine_streams[machine] = machine.stats(stream=True, decode=True)

        table_header = ["LAB HASH", "USER", "MACHINE NAME", "STATUS", "CPU %", "MEM USAGE / LIMIT", "MEM %", "NET I/O"]
        stats_table = DoubleTable([])
        stats_table.inner_row_border = True

        while True:
            machines_data = [
                table_header
            ]

            for (machine, machine_stats) in machine_streams.items():
                try:
                    result = next(machine_stats)
                except StopIteration:
                    continue

                stats = self._get_aggregate_machine_info(result)

                machines_data.append([machine.labels['lab_hash'],
                                      machine.labels['user'],
                                      machine.labels["name"],
                                      machine.status,
                                      stats["cpu_usage"],
                                      stats["mem_usage"],
                                      stats["mem_percent"],
                                      stats["net_usage"]
                                      ])

            stats_table.table_data = machines_data

            yield("TIMESTAMP: %s" % datetime.now() + "\n\n" + stats_table.table)

    @privileged
    def get_machine_info(self, machine_name, lab_hash=None, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        machines = self.docker_machine.get_machines_by_filters(machine_name=machine_name,
                                                               lab_hash=lab_hash,
                                                               user=user_name
                                                               )

        if not machines:
            raise Exception("The specified machine is not running.")
        elif len(machines) > 1:
            raise Exception("There are more than one machine matching the name `%s`." % machine_name)

        machine = machines[0]

        machine_info = utils.format_headers("Machine information") + "\n"

        machine_info += "Lab Hash: %s\n" % machine.labels['lab_hash']
        machine_info += "Machine Name: %s\n" % machine_name
        machine_info += "Real Machine Name: %s\n" % machine.name
        machine_info += "Status: %s\n" % machine.status
        machine_info += "Image: %s\n\n" % machine.image.tags[0]

        machine_stats = machine.stats(stream=False)

        machine_info += "PIDs: %d\n" % (machine_stats["pids_stats"]["current"]
                                        if "current" in machine_stats["pids_stats"] else 0)
        stats = self._get_aggregate_machine_info(machine_stats)

        machine_info += "CPU Usage: %s\n" % stats["cpu_usage"]
        machine_info += "Memory Usage: %s\n" % stats["mem_usage"]
        machine_info += "Network Usage (DL/UL): %s\n" % stats["net_usage"]

        machine_info += "======================================================================="

        return machine_info

    @privileged
    def check_image(self, image_name):
        self.docker_image.check_and_pull(image_name)

    @privileged
    def check_updates(self, settings):
        local_image_info = self.docker_image.check_local(settings.image)
        remote_image_info = self.docker_image.check_remote(settings.image)

        # Image has been built locally, so there's nothing to compare.
        local_repo_digests = local_image_info.attrs["RepoDigests"]
        if not local_repo_digests:
            return

        local_repo_digest = local_repo_digests[0]
        remote_image_digest = remote_image_info["images"][0]["digest"]

        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")

        if remote_image_digest != local_image_digest:
            utils.confirmation_prompt("A new version of image `%s` has been found on Docker Hub. "
                                      "Do you want to pull it?" % settings.image,
                                      lambda: self.docker_image.pull(settings.image),
                                      lambda: None
                                      )

    @privileged
    def get_release_version(self):
        return self.client.version()["Version"]

    def get_manager_name(self):
        return "docker"

    def get_formatted_manager_name(self):
        return "Docker (Kathara)"

    @staticmethod
    def _get_aggregate_machine_info(stats):
        network_stats = stats["networks"] if "networks" in stats else {}

        return {
            "cpu_usage": "{0:.2f}%".format(stats["cpu_stats"]["cpu_usage"]["total_usage"] /
                                           stats["cpu_stats"]["system_cpu_usage"]
                                           ) if "system_cpu_usage" in stats["cpu_stats"] else "-",
            "mem_usage": utils.human_readable_bytes(stats["memory_stats"]["usage"]) + " / " +
                         utils.human_readable_bytes(stats["memory_stats"]["limit"])
                         if "usage" in stats["memory_stats"] else "- / -",
            "mem_percent": "{0:.2f}%".format((stats["memory_stats"]["usage"] / stats["memory_stats"]["limit"]) * 100)
                           if "usage" in stats["memory_stats"] else "-",
            "net_usage": utils.human_readable_bytes(sum([net_stats["rx_bytes"]
                                                         for (_, net_stats) in network_stats.items()])
                                                    ) + " / " +
                         utils.human_readable_bytes(sum([net_stats["tx_bytes"]
                                                         for (_, net_stats) in network_stats.items()])
                                                    )
        }
