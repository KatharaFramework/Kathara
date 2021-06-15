from copy import copy
from datetime import datetime

import docker
from requests.exceptions import ConnectionError as RequestsConnectionError
from terminaltables import DoubleTable

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from .DockerPlugin import DockerPlugin
from ... import utils
from ...decorators import privileged
from ...exceptions import DockerDaemonConnectionError
from ...foundation.manager.IManager import IManager
from ...model.Link import BRIDGE_LINK_NAME
from ...utils import pack_files_for_tar


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
    __slots__ = ['client', 'docker_image', 'docker_machine', 'docker_link']

    @check_docker_status
    def __init__(self):
        self.client = docker.from_env(timeout=None, max_pool_size=utils.get_pool_size())

        docker_plugin = DockerPlugin(self.client)
        docker_plugin.check_and_download_plugin()

        self.docker_image = DockerImage(self.client)

        self.docker_machine = DockerMachine(self.client, self.docker_image)
        self.docker_link = DockerLink(self.client)

    @privileged
    def deploy_lab(self, lab, selected_machines=None, privileged_mode=False):
        if selected_machines:
            lab = copy(lab)
            lab.intersect_machines(selected_machines)

        # Deploy all lab links.
        self.docker_link.deploy_links(lab)

        # Deploy all lab machines.
        self.docker_machine.deploy_machines(lab, privileged_mode=privileged_mode)

    @privileged
    def update_lab(self, lab_diff):
        # Deploy new links (if present)
        for (_, link) in lab_diff.links.items():
            if link.name == BRIDGE_LINK_NAME:
                continue

            self.docker_link.create(link)

        # Update lab machines.
        for (_, machine) in lab_diff.machines.items():
            print(machine.name, machine.api_object)

            if machine.api_object is None:
                self.deploy_lab(lab_diff, selected_machines={machine.name})
            else:
                self.docker_machine.update(machine)

    @privileged
    def undeploy_lab(self, lab_hash, selected_machines=None):
        self.docker_machine.undeploy(lab_hash, selected_machines=selected_machines)

        self.docker_link.undeploy(lab_hash)

    @privileged
    def wipe(self, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        self.docker_machine.wipe(user=user_name)
        self.docker_link.wipe(user=user_name)

    @privileged
    def connect_tty(self, lab_hash, machine_name, shell=None, logs=False):
        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    shell=shell,
                                    logs=logs
                                    )

    @privileged
    def exec(self, lab_hash, machine_name, command):
        return self.docker_machine.exec(lab_hash, machine_name, command, tty=False)

    @privileged
    def copy_files(self, machine, guest_to_host):
        tar_data = pack_files_for_tar(machine.name, guest_to_host)
        self.docker_machine.copy_files(machine.api_object,
                                       path="/",
                                       tar_data=tar_data
                                       )

    @privileged
    def get_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        lab_info = self.docker_machine.get_machines_info(lab_hash, machine_filter=machine_name, user=user_name)

        return lab_info

    @privileged
    def get_formatted_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        table_header = ["LAB HASH", "USER", "DEVICE NAME", "STATUS", "CPU %", "MEM USAGE / LIMIT", "MEM %", "NET I/O"]
        stats_table = DoubleTable([])
        stats_table.inner_row_border = True

        lab_info = self.get_lab_info(lab_hash, machine_name, all_users)

        while True:
            machines_data = [
                table_header
            ]

            try:
                result = next(lab_info)
            except StopIteration:
                return

            if not result:
                return

            for machine_stats in result:
                machines_data.append([machine_stats['real_lab_hash'],
                                      machine_stats['user'],
                                      machine_stats['name'],
                                      machine_stats['status'],
                                      machine_stats['cpu_usage'],
                                      machine_stats['mem_usage'],
                                      machine_stats['mem_percent'],
                                      machine_stats['net_usage']
                                      ])

            stats_table.table_data = machines_data

            yield "TIMESTAMP: %s" % datetime.now() + "\n\n" + stats_table.table

    @privileged
    def get_machine_api_object(self, lab_hash, machine_name):
        return self.docker_machine.get_machine(lab_hash, machine_name)

    @privileged
    def get_machine_info(self, machine_name, lab_hash=None, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        machine_stats = self.docker_machine.get_machine_info(machine_name, lab_hash=lab_hash, user=user_name)

        return machine_stats

    @privileged
    def get_formatted_machine_info(self, machine_name, lab_hash=None, all_users=False):
        machine_stats = self.get_machine_info(machine_name, lab_hash, all_users)

        machine_info = utils.format_headers("Device information") + "\n"
        machine_info += "Lab Hash: %s\n" % machine_stats['real_lab_hash']
        machine_info += "Device Name: %s\n" % machine_stats['name']
        machine_info += "Real Device Name: %s\n" % machine_stats['real_name']
        machine_info += "Status: %s\n" % machine_stats['status']
        machine_info += "Image: %s\n\n" % machine_stats['image']
        machine_info += "PIDs: %d\n" % machine_stats['pids']
        machine_info += "CPU Usage: %s\n" % machine_stats["cpu_usage"]
        machine_info += "Memory Usage: %s\n" % machine_stats["mem_usage"]
        machine_info += "Network Usage (DL/UL): %s\n" % machine_stats["net_usage"]
        machine_info += utils.format_headers()

        return machine_info

    @privileged
    def check_image(self, image_name):
        self.docker_image.check(image_name)

    @privileged
    def get_release_version(self):
        return self.client.version()["Version"]

    @staticmethod
    def get_formatted_manager_name():
        return "Docker (Kathara)"
