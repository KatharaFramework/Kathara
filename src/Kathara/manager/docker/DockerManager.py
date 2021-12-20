import io
import logging
from copy import copy
from datetime import datetime
from typing import Set, Dict, Generator, Any, Tuple, List

import docker
import docker.models.containers
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
from ...model.Lab import Lab
from ...model.Link import BRIDGE_LINK_NAME
from ...model.Machine import Machine
from ...setting.Setting import Setting
from ...utils import pack_files_for_tar


def pywin_import_stub():
    """Stub module of pywintypes for Unix systems (so it won't raise any `module not found` exception)."""
    import types
    pywintypes = types.ModuleType("pywintypes")
    pywintypes.error = RequestsConnectionError
    return pywintypes


def pywin_import_win():
    import pywintypes
    return pywintypes


def check_docker_status(method):
    """Decorator function to check if Docker daemon is running properly."""
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
    """The class responsible to interact between Kathara and the Docker APIs."""
    __slots__ = ['client', 'docker_image', 'docker_machine', 'docker_link']

    @check_docker_status
    def __init__(self) -> None:
        remote_url = Setting.get_instance().remote_url
        if remote_url is None:
            self.client: docker.DockerClient = docker.from_env(timeout=None, max_pool_size=utils.get_pool_size())
        else:
            tls_config = docker.tls.TLSConfig(ca_cert=Setting.get_instance().cert_path)
            self.client: docker.DockerClient = docker.DockerClient(base_url=remote_url, timeout=None,
                                                                   max_pool_size=utils.get_pool_size(),
                                                                   tls=tls_config)

        docker_plugin = DockerPlugin(self.client)
        docker_plugin.check_and_download_plugin()

        self.docker_image: DockerImage = DockerImage(self.client)

        self.docker_machine: DockerMachine = DockerMachine(self.client, self.docker_image)
        self.docker_link: DockerLink = DockerLink(self.client)

    @privileged
    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Set[str]): If not None, deploy only the specified devices.

        Returns:
            None
        """
        selected_links = None
        if selected_machines:
            selected_links = lab.get_links_from_machines(selected_machines)

        # Deploy all lab links.
        self.docker_link.deploy_links(lab, selected_links=selected_links)

        # Deploy all lab machines.
        self.docker_machine.deploy_machines(lab, selected_machines=selected_machines)

    @privileged
    def update_lab(self, lab: Lab) -> None:
        """Update a running network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.

        Returns:
            None
        """
        # Deploy new links (if present)
        for (_, link) in lab.links.items():
            if link.name == BRIDGE_LINK_NAME:
                continue

            self.docker_link.create(link)

        # Update lab devices.
        for (_, machine) in lab.machines.items():
            # Device is not deployed, deploy it
            if machine.api_object is None:
                self.deploy_lab(lab, selected_machines={machine.name})
            else:
                # Device already deployed, update it
                self.docker_machine.update(machine)

    @privileged
    def undeploy_lab(self, lab_hash: str, selected_machines: Set[str] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_machines (Set[str]): If not None, undeploy only the specified devices.

        Returns:
            None
        """
        self.docker_machine.undeploy(lab_hash, selected_machines=selected_machines)

        self.docker_link.undeploy(lab_hash)

    @privileged
    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        If multiuser scenarios are active, undeploy only current user devices.

        Args:
        all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
           running network scenarios of all users.

        Returns:
            None
        """
        if Setting.get_instance().remote_url is not None and all_users:
            all_users = False
            logging.warning("Cannot wipe devices of other users with a remote Docker connection.")

        user_name = utils.get_current_user_name() if not all_users else None

        self.docker_machine.wipe(user=user_name)
        self.docker_link.wipe(user=user_name)

    @privileged
    def connect_tty(self, lab_hash: str, machine_name: str, shell: str = None, logs: bool = False) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            machine_name (str): The name of the device to connect.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.

        Returns:
            None
        """
        user_name = utils.get_current_user_name()

        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    user=user_name,
                                    shell=shell,
                                    logs=logs
                                    )

    @privileged
    def exec(self, lab_hash: str, machine_name: str, command: str) -> Generator[Tuple[bytes, bytes], None, None]:
        """Exec a command on a device in a running network scenario.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            machine_name (str): The name of the device to connect.
            command (str): The command to exec on the device.

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.
        """
        user_name = utils.get_current_user_name()

        return self.docker_machine.exec(lab_hash, machine_name, command, user=user_name, tty=False)

    @privileged
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running machine object. It must have the api_object field populated.
            guest_to_host (Dict[str, io.IOBase]): A dict containing the device path as key and
                fileobj to copy in path as value.

        Returns:
            None
        """
        tar_data = pack_files_for_tar(guest_to_host)

        self.docker_machine.copy_files(machine.api_object,
                                       path="/",
                                       tar_data=tar_data
                                       )

    @privileged
    def get_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> \
            Generator[Dict[str, Any], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (str): If not None, return information of the corresponding network scenario.
            machine_name (str): If not None, return information of the specified device.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, Any], None, None]: A generator containing dicts containing device names as keys and
              their info as values.
        """
        user_name = utils.get_current_user_name() if not all_users else None

        lab_info = self.docker_machine.get_machines_info(lab_hash, machine_name=machine_name, user=user_name)

        return lab_info

    @privileged
    def get_formatted_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> str:
        """Return a formatted string with the information about the running devices.

        Args:
            lab_hash (str): If not None, return information of the corresponding network scenario.
            machine_name (str): If not None, return information of the specified device.
            all_users (bool): If True, return information about the device of all users.

        Returns:
             str: String containing devices info
        """
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
    def get_machine_api_object(self, lab_hash: str, machine_name: str) -> docker.models.containers.Container:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            lab_hash (str): The hash of the network scenario.
            machine_name (str): The name of the device.

        Returns:
            docker.models.containers.Container: docker machine api object.
        """
        user_name = utils.get_current_user_name()

        return self.docker_machine.get_machine_api_object(lab_hash, machine_name, user=user_name)

    @privileged
    def get_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) \
            -> List[Dict[str, Any]]:
        """Return information of running devices with a specified name.

        Args:
            machine_name (str): The device name.
            lab_hash (str): If not None, search the device in the specified network scenario.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            List[Dict[str, Any]]: A list of dicts containing the devices info.
        """
        user_name = utils.get_current_user_name() if not all_users else None

        machines_stats = self.docker_machine.get_machine_info(machine_name, lab_hash=lab_hash, user=user_name)

        return machines_stats

    @privileged
    def get_formatted_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) -> str:
        """Return formatted information of running devices with a specified name.

        Args:
            machine_name (str): The device name.
            lab_hash (str): If not None, search the device in the specified network scenario.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            str: The formatted devices properties.
        """
        machines_stats = self.get_machine_info(machine_name, lab_hash, all_users)

        machines_info = []

        for machine_stats in machines_stats:
            machine_info = utils.format_headers("Device information") + "\n"
            machine_info += "Lab Hash: %s\n" % machine_stats['real_lab_hash']
            machine_info += "Device Name: %s\n" % machine_stats['name']
            machine_info += "Real Device Name: %s\n" % machine_stats['real_name']
            machine_info += "Status: %s\n" % machine_stats['status']
            machine_info += "Image: %s\n\n" % machine_stats['image']
            machine_info += "PIDs: %s\n" % machine_stats['pids']
            machine_info += "CPU Usage: %s\n" % machine_stats["cpu_usage"]
            machine_info += "Memory Usage: %s\n" % machine_stats["mem_usage"]
            machine_info += "Network Usage (DL/UL): %s\n" % machine_stats["net_usage"]
            machine_info += utils.format_headers()

            machines_info.append(machine_info)

        return "\n\n".join(machines_info)

    @privileged
    def check_image(self, image_name: str) -> None:
        """Check if the specified image is valid.

        Args:
            image_name (str): The name of the image

        Returns:
            None

        Raises:
            ConnectionError: The image is not locally available and there is no connection to a remote image repository.
            Exception: The image is not found.
        """
        self.docker_image.check(image_name)

    @privileged
    def get_release_version(self) -> str:
        """Return the current manager version.

        Returns:
            str: The current manager version.
        """
        return self.client.version()["Version"]

    @staticmethod
    def get_formatted_manager_name() -> str:
        """Return a formatted string containing the current manager name.

        Returns:
            str: A formatted string containing the current manager name.
        """
        return "Docker (Kathara)"
