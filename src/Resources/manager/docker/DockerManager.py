from datetime import datetime

import docker

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from ... import utils
from ...foundation.manager.IManager import IManager
from ...model.Link import BRIDGE_LINK_NAME


def win_import():
    import pywintypes

utils.exec_by_platform(lambda: None, win_import, lambda: None)


def check_docker_status(method):
    """
    Decorator function to check if Docker daemon is up and running.
    """
    def check_status(*args, **kw):
        client = args[0].client
        try:
            client.ping()
            return method(*args, **kw)
        except ConnectionError:
            raise Exception("Can not connect to Docker Daemon. Maybe you have not started it?")
        except pywintypes.error:
            raise Exception("Can not connect to Docker Daemon. Maybe you have not started it?")

    return check_status


class DockerManager(IManager):
    __slots__ = ['docker_image', 'docker_machine', 'docker_link', 'client']

    def __init__(self):
        self.client = docker.from_env()

        self.docker_image = DockerImage(self.client)

        self.docker_machine = DockerMachine(self.client, self.docker_image)
        self.docker_link = DockerLink(self.client)

    @check_docker_status
    def deploy_lab(self, lab):
        # Deploy all lab links.
        for (_, link) in lab.links.items():
            self.docker_link.deploy(link)

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.docker_link.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.api_object = docker_bridge

        # Deploy all lab machines.
        for (_, machine) in lab.machines.items():
            self.docker_machine.deploy(machine)

        for (_, machine) in lab.machines.items():
            self.docker_machine.start(machine)

    @check_docker_status
    def update_lab(self, lab_diff):
        # Deploy new links (if present)
        for (_, link) in lab_diff.links.items():
            self.docker_link.deploy(link)

        # Update lab machines.
        for (_, machine) in lab_diff.machines.items():
            self.docker_machine.update(machine)

    @check_docker_status
    def undeploy_lab(self, lab_hash, selected_machines=None):
        self.docker_machine.undeploy(lab_hash,
                                     selected_machines=selected_machines
                                     )
        self.docker_link.undeploy(lab_hash)

    @check_docker_status
    def wipe(self):
        self.docker_machine.wipe()
        self.docker_link.wipe()

    @check_docker_status
    def connect_tty(self, lab_hash, machine_name, shell):
        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    shell=shell
                                    )

    @check_docker_status
    def get_lab_info(self, lab_hash=None, machine_name=None):
        container_name = self.docker_machine.get_container_name(machine_name, lab_hash) if machine_name else None

        machines = self.docker_machine.get_machines_by_filters(lab_hash=lab_hash, container_name=container_name)

        if not machines:
            if not lab_hash:
                raise Exception("No machines running.")
            else:
                raise Exception("Lab is not started.")

        machines = sorted(machines, key=lambda x: x.name)

        machine_streams = {}

        for machine in machines:
            machine_streams[machine] = machine.stats(stream=True, decode=True)

        while True:
            all_stats = "TIMESTAMP: %s\n\n" % datetime.now()
            all_stats += "LAB HASH\t\tMACHINE NAME\tSTATUS\t\tCPU %\tMEM USAGE / LIMIT\tMEM %\tNET I/O\n"

            for (machine, machine_stats) in machine_streams.items():
                result = next(machine_stats)
                stats = self._get_aggregate_machine_info(result)

                all_stats += "%s\t%s\t\t%s\t\t%s\t%s\t%s\t%s\n" % (machine.labels['lab_hash'],
                                                                   machine.labels["name"],
                                                                   machine.status,
                                                                   stats["cpu_usage"],
                                                                   stats["mem_usage"],
                                                                   stats["mem_percent"],
                                                                   stats["net_usage"]
                                                                   )

            yield(all_stats)

    @check_docker_status
    def get_machine_info(self, machine_name, lab_hash=None):
        container_name = self.docker_machine.get_container_name(machine_name, lab_hash)
        machines = self.docker_machine.get_machines_by_filters(container_name=container_name, lab_hash=lab_hash)

        if not machines:
            raise Exception("The specified machine is not running.")
        elif len(machines) > 1:
            raise Exception("There are more than one machine matching the name `%d`." % machine_name)

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

    @check_docker_status
    def check_image(self, image_name):
        try:
            self.docker_image.check_and_pull(image_name)
        except Exception as e:
            raise Exception(str(e))

    @check_docker_status
    def check_updates(self, settings):
        local_image_info = self.docker_image.check_local(settings.image)
        remote_image_info = self.docker_image.check_remote(settings.image)

        remote_image_digest = remote_image_info["images"][0]["digest"]
        local_repo_digest = local_image_info.attrs["RepoDigests"][0]
        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")

        if remote_image_digest != local_image_digest:
            utils.confirmation_prompt("A new version of image `%s` has been found on Docker Hub. "
                                      "Do you want to pull it?" % settings.image,
                                      lambda: self.docker_image.pull(settings.image),
                                      lambda: None
                                      )

    @check_docker_status
    def get_release_version(self):
        return self.client.version()["Version"]

    @staticmethod
    def _get_aggregate_machine_info(stats):
        network_stats = stats["networks"] if "networks" in stats else {}

        return {
            "cpu_usage": "{0:.2f}%".format(stats["cpu_stats"]["cpu_usage"]["total_usage"] /
                                           stats["cpu_stats"]["system_cpu_usage"]
                                           ) if "system_cpu_usage" in stats["cpu_stats"] else "-",
            "mem_usage": utils.human_readable_bytes(stats["memory_stats"]["usage"]) + " / " +
                         utils.human_readable_bytes(stats["memory_stats"]["limit"])
                         if "usage" in stats["memory_stats"] else "- / -\t\t",
            "mem_percent": "{0:.2f}%".format((stats["memory_stats"]["usage"] / stats["memory_stats"]["limit"]) * 100)
                           if "usage" in stats["memory_stats"] else "-",
            "net_usage": utils.human_readable_bytes(sum([net_stats["rx_bytes"]
                                                         for (_, net_stats) in network_stats.items()])
                                                    ) + " / " +
                         utils.human_readable_bytes(sum([net_stats["tx_bytes"]
                                                         for (_, net_stats) in network_stats.items()])
                                                    )
        }
