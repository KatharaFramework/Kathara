import io
import logging
from typing import Set, Dict, Generator, Tuple, List, Optional

import docker
import docker.models.containers
import docker.models.networks
from requests.exceptions import ConnectionError as RequestsConnectionError

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from .DockerPlugin import DockerPlugin
from .stats.DockerLinkStats import DockerLinkStats
from .stats.DockerMachineStats import DockerMachineStats
from ... import utils
from ...decorators import privileged
from ...exceptions import DockerDaemonConnectionError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.Link import Link
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
    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None
        """
        if not machine.lab:
            raise Exception("Machine `%s` is not associated to a network scenario." % machine.name)

        self.docker_link.deploy_links(machine.lab, selected_links={x.name for x in machine.interfaces.values()})
        self.docker_machine.deploy_machines(machine.lab, selected_machines={machine.name})

    @privileged
    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        if not link.lab:
            raise Exception("Collision domain `%s` is not associated to a network scenario." % link.name)

        self.docker_link.deploy_links(link.lab, selected_links={link.name})

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
    def connect_machine_to_link(self, machine: Machine, link: Link) -> None:
        """Connect a Kathara device to a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        if not machine.lab:
            raise Exception("Machine `%s` is not associated to a network scenario." % machine.name)

        if machine.name not in link.machines:
            raise Exception("Machine `%s` is not connected to collision domain `%s`." % (machine.name, link.name))

        self.deploy_link(link)
        self.docker_machine.connect_to_link(machine, link)

    @privileged
    def undeploy_machine(self, machine: Machine) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None
        """
        if not machine.lab:
            raise Exception("Machine `%s` is not associated to a network scenario." % machine.name)

        self.docker_machine.undeploy(machine.lab.hash, selected_machines={machine.name})
        self.docker_link.undeploy(machine.lab.hash, selected_links={x.name for x in machine.interfaces.values()})

    @privileged
    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        if not link.lab:
            raise Exception("Collision domain `%s` is not associated to a network scenario." % link.name)

        self.docker_link.undeploy(link.lab.hash, selected_links={link.name})

    @privileged
    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                     selected_machines: Optional[Set[str]] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (Optional[str]): The name of the network scenario. Can be used as an alternative to lab_hash.
                If None, lab_hash should be set.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.

        Returns:
            None

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

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
    def connect_tty(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                    shell: str = None, logs: bool = False) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine_name (str): The name of the device to connect.
            lab_hash (str): The hash of the network scenario where the device is deployed.
            lab_name (str): The name of the network scenario where the device is deployed.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.

        Returns:
            None

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name()

        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    user=user_name,
                                    shell=shell,
                                    logs=logs
                                    )

    @privileged
    def exec(self, machine_name: str, command: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None) -> \
            Generator[Tuple[bytes, bytes], None, None]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine_name (str): The name of the device to connect.
            command (str): The command to exec on the device.
            lab_hash (Optional[str]): The hash of the network scenario where the device is deployed.
            lab_name (Optional[str]): The name of the network scenario where the device is deployed.

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        user_name = utils.get_current_user_name()
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        return self.docker_machine.exec(lab_hash, machine_name, command, user=user_name, tty=False)

    @privileged
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
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
    def get_machine_api_object(self, machine_name: str, lab_hash: str = None, lab_name: str = None,
                               all_users: bool = False) -> docker.models.containers.Container:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            machine_name (str): The name of the device.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_hash should be set.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            docker.models.containers.Container: Docker API object of devices.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        user_name = utils.get_current_user_name() if not all_users else None
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        containers = self.docker_machine.get_machines_api_objects_by_filters(
            lab_hash=lab_hash, machine_name=machine_name, user=user_name
        )
        if containers:
            return containers.pop()

        raise Exception(f"Device {machine_name} not found.")

    def get_machines_api_objects(self, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> \
            List[docker.models.containers.Container]:
        """Return API objects of running devices.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            List[docker.models.containers.Container]: Docker API objects of devices.
        """
        user_name = utils.get_current_user_name() if not all_users else None
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        return self.docker_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    def get_link_api_object(self, link_name: str, lab_hash: str = None, lab_name: str = None,
                            all_users: bool = False) -> docker.models.networks.Network:
        """Return the corresponding API object of a collision domain in a network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_hash should be set.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            docker.models.networks.Network: Docker API object of the network.

        Raises:
            Exception: You must specify a running network scenario hash or name.
            Exception: Collision Domain not found.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        user_name = utils.get_current_user_name() if not all_users else None
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        networks = self.docker_link.get_links_api_objects_by_filters(
            lab_hash=lab_hash, link_name=link_name, user=user_name
        )
        if networks:
            return networks.pop()

        raise Exception(f"Collision Domain {link_name} not found.")

    def get_links_api_objects(self, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> \
            List[docker.models.networks.Network]:
        """Return API objects of collision domains in a network scenario.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            List[docker.models.networks.Network]: Docker API objects of networks.
        """
        user_name = utils.get_current_user_name() if not all_users else None
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        return self.docker_link.get_links_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    @privileged
    def get_machines_stats(self, lab_hash: str = None, lab_name: str = None, machine_name: str = None,
                           all_users: bool = False) -> Generator[Dict[str, DockerMachineStats], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
            machine_name (str): If specified return all the devices with machine_name.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, DockerMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and DockerMachineStats objects as values.
        """
        user_name = utils.get_current_user_name() if not all_users else None
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        return self.docker_machine.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name,
                                                      user=user_name)

    @privileged
    def get_machine_stats(self, machine_name: str, lab_hash: str = None,
                          lab_name: str = None, all_users: bool = False) -> Generator[DockerMachineStats, None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine_name (str): The device name.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
                If None, lab_hash should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[DockerMachineStats, None, None]: A generator containing DockerMachineStats objects with
            the device info.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        machines_stats = self.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name, all_users=all_users)
        (_, machine_stats) = next(machines_stats).popitem()

        yield machine_stats

    def get_links_stats(self, lab_hash: str = None, lab_name: str = None, link_name: str = None,
                        all_users: bool = False) -> Generator[Dict[str, DockerLinkStats], None, None]:
        """Return information about deployed Docker networks.

        Args:
           lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
           lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
           link_name (str): If specified return all the networks with link_name.
           all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, DockerLinkStats], None, None]: A generator containing dicts that has API Object
                identifier as keys and DockerLinksStats objects as values.
        """
        user_name = utils.get_current_user_name() if not all_users else None
        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        return self.docker_link.get_links_stats(lab_hash=lab_hash, link_name=link_name, user=user_name)

    def get_link_stats(self, link_name: str, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> \
            Generator[DockerLinkStats, None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link_name (str): The link name.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
                If None, lab_hash should be set.
            all_users (bool): If True, search the network among all the users networks.

        Returns:
            Generator[DockerLinkStats, None, None]: A generator containing DockerLinkStats objects with the network
                statistics.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        links_stats = self.get_links_stats(lab_hash=lab_hash, link_name=link_name, all_users=all_users)
        (_, link_stats) = next(links_stats).popitem()

        yield link_stats

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
