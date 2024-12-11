import io
import logging
from typing import Set, Dict, Generator, Tuple, List, Optional, Union

import docker
import docker.models.containers
import docker.models.networks
from docker.errors import DockerException
from requests.exceptions import ConnectionError as RequestsConnectionError

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from .DockerPlugin import DockerPlugin
from .exec_stream.DockerExecStream import DockerExecStream
from .stats.DockerLinkStats import DockerLinkStats
from .stats.DockerMachineStats import DockerMachineStats
from ... import utils
from ...decorators import privileged
from ...exceptions import DockerDaemonConnectionError, LinkNotFoundError, MachineCollisionDomainError, \
    InvocationError, LabNotFoundError, MachineNotRunningError
from ...exceptions import MachineNotFoundError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.Link import Link
from ...model.Machine import Machine
from ...setting.Setting import Setting
from ...types import SharedCollisionDomainsOption
from ...utils import pack_files_for_tar, import_pywintypes, \
    check_required_single_not_none_var, check_single_not_none_var

pywintypes = import_pywintypes()


def check_docker_status(method):
    """Decorator function to check if Docker daemon is running properly."""

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
            raise DockerDaemonConnectionError(str(e))
        except pywintypes.error as e:
            raise DockerDaemonConnectionError(str(e))

    return check_docker


class DockerManager(IManager):
    """The class responsible to interact between Kathara and the Docker APIs."""
    __slots__ = ['client', 'docker_image', 'docker_machine', 'docker_link']

    @check_docker_status
    def __init__(self) -> None:
        remote_url = Setting.get_instance().remote_url
        try:
            if remote_url is None:
                self.client: docker.DockerClient = docker.from_env(timeout=None, max_pool_size=utils.get_pool_size())
            else:
                tls_config = docker.tls.TLSConfig(ca_cert=Setting.get_instance().cert_path)
                self.client: docker.DockerClient = docker.DockerClient(
                    base_url=remote_url, timeout=None, max_pool_size=utils.get_pool_size(), tls=tls_config
                )
        except DockerException as e:
            raise DockerDaemonConnectionError(str(e))

        docker_plugin = DockerPlugin(self.client)
        docker_plugin.check_and_download_plugin()

        self.docker_image: DockerImage = DockerImage(self.client)

        self.docker_machine: DockerMachine = DockerMachine(self.client, self.docker_image)
        self.docker_link: DockerLink = DockerLink(self.client, docker_plugin)

    @privileged
    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            PrivilegeError: If the user start the device in privileged mode without having root privileges.
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        machine.check()

        self.docker_link.deploy_links(machine.lab, selected_links={x.link.name for x in machine.interfaces.values()})
        self.docker_machine.deploy_machines(machine.lab, selected_machines={machine.name})

    @privileged
    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError("Collision domain `%s` is not associated to a network scenario." % link.name)

        self.docker_link.deploy_links(link.lab, selected_links={link.name})

    @privileged
    def deploy_lab(self, lab: Lab, selected_machines: Optional[Set[str]] = None,
                   excluded_machines: Optional[Set[str]] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Optional[Set[str]]): If not None, deploy only the specified devices.
            excluded_machines (Optional[Set[str]]): If not None, exclude devices from being deployed.

        Returns:
            None

        Raises:
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
            OSError: If any link in the network scenario is attached to external interfaces and the host OS is not LINUX.
            PrivilegeError: If the user start the network scenario in privileged mode without having root privileges.
            MachineNotFoundError: If the specified devices are not in the network scenario.
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
        lab.check_integrity()

        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either select or exclude devices.")

        if selected_machines and not lab.has_machines(selected_machines):
            machines_not_in_lab = selected_machines - set(lab.machines.keys())
            raise MachineNotFoundError(f"The following devices are not in the network scenario: {machines_not_in_lab}.")

        if excluded_machines and not lab.has_machines(excluded_machines):
            machines_not_in_lab = excluded_machines - set(lab.machines.keys())
            raise MachineNotFoundError(f"The following devices are not in the network scenario: {machines_not_in_lab}.")

        selected_links = None
        if selected_machines:
            selected_links = lab.get_links_from_machines(selected_machines)

        excluded_links = None
        if excluded_machines:
            # Get the links of remaining machines
            running_links = lab.get_links_from_machines(set(lab.machines.keys()) - excluded_machines)
            # Get the links of the excluded machines and get the diff with the running ones
            # The remaining are the ones to delete
            excluded_links = lab.get_links_from_machines(excluded_machines) - running_links

        # Deploy all lab links.
        self.docker_link.deploy_links(lab, selected_links=selected_links, excluded_links=excluded_links)

        # Deploy all lab machines.
        self.docker_machine.deploy_machines(
            lab, selected_machines=selected_machines, excluded_machines=excluded_machines
        )

    @privileged
    def connect_machine_to_link(self, machine: Machine, link: Link, mac_address: Optional[str] = None) -> None:
        """Create a new interface on a running Kathara device and connect it to a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): A Kathara collision domain object.
            mac_address (Optional[str]): The MAC address to assign to the interface.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            MachineCollisionDomainConflictError: If the device is already connected to the collision domain.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        if not machine.api_object:
            raise MachineNotRunningError(machine.name)

        machine.api_object.reload()
        if machine.api_object.status != "running":
            raise MachineNotRunningError(machine.name)

        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        if machine.name in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{machine.name}` is already connected to collision domain `{link.name}`."
            )

        iface_number = None
        if machine.is_bridged():
            if 'bridged_iface' not in machine.meta:
                machine.add_meta('bridged_iface', int(machine.api_object.labels['bridged_iface']))
            if machine.meta['bridged_iface'] > max(machine.interfaces.keys()):
                iface_number = machine.meta['bridged_iface'] + 1
            else:
                iface_number = max(machine.interfaces.keys()) + 1

        interface = machine.add_interface(link, mac_address=mac_address, number=iface_number)

        self.deploy_link(link)
        self.docker_machine.connect_interface(machine, interface)

    @privileged
    def disconnect_machine_from_link(self, machine: Machine, link: Link) -> None:
        """Disconnect a running Kathara device from a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): The Kathara collision domain from which disconnect the running device.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            MachineCollisionDomainConflictError: If the device is not connected to the collision domain.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        if not machine.api_object:
            raise MachineNotRunningError(machine.name)

        machine.api_object.reload()
        if machine.api_object.status != "running":
            raise MachineNotRunningError(machine.name)

        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        if machine.name not in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{machine.name}` is not connected to collision domain `{link.name}`."
            )

        machine.remove_interface(link)

        self.docker_machine.disconnect_from_link(machine, link)
        self.undeploy_link(link)

    @privileged
    def undeploy_machine(self, machine: Machine) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        self.docker_machine.undeploy(machine.lab.hash, selected_machines={machine.name})
        self.docker_link.undeploy(machine.lab.hash, selected_links={x.link.name for x in machine.interfaces.values()})

    @privileged
    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        self.docker_link.undeploy(link.lab.hash, selected_links={link.name})

    @privileged
    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                     selected_machines: Optional[Set[str]] = None,
                     excluded_machines: Optional[Set[str]] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.
            excluded_machines (Optional[Set[str]]): If not None, exclude devices from being undeployed.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified,
                or if both `selected_machines` and `excluded_machines` are specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either select or exclude devices.")

        self.docker_machine.undeploy(lab_hash, selected_machines=selected_machines, excluded_machines=excluded_machines)

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
                    lab: Optional[Lab] = None, shell: str = None, logs: bool = False,
                    wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine_name (str): The name of the device to connect.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before connecting. If a tuple is provided, the first value indicates the number of retries
                before stopping waiting and the second value indicates the time interval to wait for each retry.
                Default is True.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name()

        self.docker_machine.connect(lab_hash=lab_hash,
                                    machine_name=machine_name,
                                    user=user_name,
                                    shell=shell,
                                    logs=logs,
                                    wait=wait
                                    )

    def connect_tty_obj(self, machine: Machine, shell: str = None, logs: bool = False,
                        wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine (Machine): The device to connect.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before connecting. If a tuple is provided, the first value indicates the number of retries
                before stopping waiting and the second value indicates the time interval to wait for each retry.
                Default is True.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        self.connect_tty(machine.name, lab=machine.lab, shell=shell, logs=logs, wait=wait)

    @privileged
    def exec(self, machine_name: str, command: Union[List[str], str], lab_hash: Optional[str] = None,
             lab_name: Optional[str] = None, lab: Optional[Lab] = None, wait: Union[bool, Tuple[int, float]] = False,
             stream: bool = True) -> Union[DockerExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine_name (str): The name of the device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a DockerExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[DockerExecStream, Tuple[bytes, bytes, int]]: A DockerExecStream object or
            a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotRunningError: If the specified device is not running.
            ValueError: If the wait values is neither a boolean nor a tuple, or an invalid tuple.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name()
        return self.docker_machine.exec(
            lab_hash, machine_name, command, user=user_name, tty=False, wait=wait, stream=stream
        )

    def exec_obj(self, machine: Machine, command: Union[List[str], str], wait: Union[bool, Tuple[int, float]] = False,
                 stream: bool = True) -> Union[DockerExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine (Machine): The device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a DockerExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[DockerExecStream, Tuple[bytes, bytes, int]]: A DockerExecStream object or
            a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
            ValueError: If the wait values is neither a boolean nor a tuple, or an invalid tuple.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        return self.exec(machine.name, command, lab=machine.lab, wait=wait, stream=stream)

    @privileged
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, Union[str, io.IOBase]]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, Union[str, io.IOBase]]): A dict containing the device path as key and a
                fileobj to copy in path as value or a path to a file.

        Returns:
            None
        """
        tar_data = pack_files_for_tar(guest_to_host)

        self.docker_machine.copy_files(machine.api_object,
                                       path="/",
                                       tar_data=tar_data
                                       )

    @privileged
    def get_machine_api_object(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                               lab: Optional[Lab] = None, all_users: bool = False) \
            -> docker.models.containers.Container:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            machine_name (str): The name of the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            docker.models.containers.Container: Docker API object of devices.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotFoundError: If the specified device is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        containers = self.docker_machine.get_machines_api_objects_by_filters(
            lab_hash=lab_hash, machine_name=machine_name, user=user_name
        )
        if containers:
            return containers.pop()

        raise MachineNotFoundError(f"Device `{machine_name}` not found.")

    @privileged
    def get_machines_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                                 lab: Optional[Lab] = None, all_users: bool = False) \
            -> List[docker.models.containers.Container]:
        """Return API objects of running devices.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            List[docker.models.containers.Container]: Docker API objects of devices.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    @privileged
    def get_link_api_object(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                            lab: Optional[Lab] = None, all_users: bool = False) -> docker.models.networks.Network:
        """Return the corresponding API object of a collision domain in a network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            docker.models.networks.Network: Docker API object of the network.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            LinkNotFoundError: If the collision domain is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        networks = self.docker_link.get_links_api_objects_by_filters(
            lab_hash=lab_hash, link_name=link_name, user=user_name
        )
        if networks:
            return networks.pop()

        raise LinkNotFoundError(f"Collision Domain `{link_name}` not found.")

    @privileged
    def get_links_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                              lab: Optional[Lab] = None, all_users: bool = False) \
            -> List[docker.models.networks.Network]:
        """Return API objects of collision domains in a network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            List[docker.models.networks.Network]: Docker API objects of networks.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_link.get_links_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    @privileged
    def get_lab_from_api(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None) -> Lab:
        """Return the network scenario (specified by the hash or name), building it from API objects.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name. If None, lab_name should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash. If None, lab_hash should be set.

        Returns:
            Lab: The built network scenario.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        if not lab_hash and not lab_name:
            raise InvocationError("You must specify a running network scenario hash or name.")

        if lab_name:
            reconstructed_lab = Lab(lab_name)
        else:
            reconstructed_lab = Lab("reconstructed_lab")
            reconstructed_lab.hash = lab_hash

        lab_containers = self.get_machines_api_objects(lab_hash=reconstructed_lab.hash)
        lab_networks = dict(
            map(lambda x: (x.name, x), self.get_links_api_objects(
                lab_hash=reconstructed_lab.hash \
                    if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED else None,
                all_users=Setting.get_instance().shared_cds == SharedCollisionDomainsOption.USERS
            ))
        )

        for container in lab_containers:
            container.reload()
            device = reconstructed_lab.get_or_new_machine(container.labels["name"])
            device.api_object = container

            # Rebuild device metas
            # NOTE: We cannot rebuild "exec", "ipv6" and "num_terms" meta.
            device.add_meta("privileged", container.attrs["HostConfig"]["Privileged"])
            device.add_meta("image", container.attrs["Config"]["Image"])
            device.add_meta("shell", container.attrs["Config"]["Labels"]["shell"])

            # Memory is always returned in MBytes
            if container.attrs['HostConfig']['Memory'] > 0:
                device.add_meta("mem", f"{int(container.attrs['HostConfig']['Memory'] / (1024 ** 2))}M")

            # Reconvert nanocpus to a value passed by the user
            if container.attrs["HostConfig"]["NanoCpus"] > 0:
                device.add_meta("cpu", container.attrs["HostConfig"]["NanoCpus"] / 1000000000)

            for env in container.attrs["Config"]["Env"]:
                device.add_meta("env", env)

            # Reconvert ports to the device format
            if container.attrs['HostConfig']['PortBindings']:
                for port_info, port_data in container.attrs['HostConfig']['PortBindings'].items():
                    (guest_port, protocol) = port_info.split('/')
                    host_port = port_data[0]["HostPort"]
                    device.meta["ports"][(int(host_port), protocol)] = int(guest_port)

            # Reassign sysctls directly
            device.meta["sysctls"] = container.attrs["HostConfig"]["Sysctls"]

            if "none" not in container.attrs["NetworkSettings"]["Networks"]:
                if "bridge" in container.attrs["NetworkSettings"]["Networks"].keys():
                    device.add_meta("bridged", True)
                    device.add_meta("bridged_iface", int(container.labels['bridged_iface']))
                    container.attrs["NetworkSettings"]["Networks"].pop("bridge")

                networks = sorted(container.attrs["NetworkSettings"]["Networks"].items(),
                                  key=lambda x: x[1]["DriverOpts"]["kathara.iface"])

                for network_name, network_options in networks:
                    network = lab_networks[network_name]
                    link = reconstructed_lab.get_or_new_link(network.attrs["Labels"]["name"])
                    link.api_object = network

                    iface_mac_addr = None
                    if network_options["DriverOpts"] is not None:
                        if "kathara.mac_addr" in network_options["DriverOpts"]:
                            iface_mac_addr = network_options["DriverOpts"]["kathara.mac_addr"]

                    device.add_interface(link, mac_address=iface_mac_addr,
                                         number=int(network_options["DriverOpts"]["kathara.iface"]))

        return reconstructed_lab

    @privileged
    def update_lab_from_api(self, lab: Lab) -> None:
        """Update the passed network scenario from API objects.

        Args:
            lab (Lab): The network scenario to update.
        """
        running_containers = self.get_machines_api_objects(lab_hash=lab.hash)

        deployed_networks = dict(
            map(lambda x: (x.name, x), self.get_links_api_objects(
                lab_hash=lab.hash \
                    if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED else None,
                all_users=Setting.get_instance().shared_cds == SharedCollisionDomainsOption.USERS
            ))
        )
        for network in deployed_networks.values():
            network.reload()

        deployed_networks_by_link_name = dict(
            map(lambda x: (x.attrs["Labels"]["name"], x), deployed_networks.values())
        )

        for container in running_containers:
            container.reload()
            device = lab.get_or_new_machine(container.labels["name"])
            device.api_object = container

            # Collision domains declared in the network scenario
            static_links = set([x.link for x in device.interfaces.values()])
            # Interfaces currently attached to the device
            if "bridge" in container.attrs["NetworkSettings"]["Networks"].keys():
                container.attrs["NetworkSettings"]["Networks"].pop("bridge")

            if "none" in container.attrs["NetworkSettings"]["Networks"].keys():
                container.attrs["NetworkSettings"]["Networks"].pop("none")

            current_ifaces = [
                (lab.get_or_new_link(deployed_networks[name].attrs["Labels"]["name"]), options)
                for name, options in sorted(container.attrs["NetworkSettings"]["Networks"].items(),
                                            key=lambda x: x[1]["DriverOpts"]["kathara.iface"])
            ]

            # Collision domains currently attached to the device
            current_links = set(map(lambda x: x[0], current_ifaces))
            # Collision domains attached at runtime to the device
            dynamic_links = current_links - static_links
            # Static collision domains detached at runtime from the device
            deleted_links = static_links - current_links

            for link in static_links:
                if link.name in deployed_networks_by_link_name:
                    link.api_object = deployed_networks_by_link_name[link.name]

            current_ifaces = dict([(x[0].name, x[1]) for x in current_ifaces])
            for link in dynamic_links:
                link.api_object = deployed_networks_by_link_name[link.name]
                iface_options = current_ifaces[link.name]
                iface_mac_addr = None
                if iface_options["DriverOpts"] is not None:
                    if "kathara.mac_addr" in iface_options["DriverOpts"]:
                        iface_mac_addr = iface_options["DriverOpts"]["kathara.mac_addr"]

                device.add_interface(link, mac_address=iface_mac_addr,
                                     number=int(iface_options["DriverOpts"]["kathara.iface"]))

            for link in deleted_links:
                device.remove_interface(link)

    @privileged
    def get_machines_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                           lab: Optional[Lab] = None, machine_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, DockerMachineStats], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            machine_name (str): If specified return all the devices with machine_name.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, DockerMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and DockerMachineStats objects as values.

        Raises:
            InvocationError: If more than one param among lab_hash, lab_name and lab is specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)

        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_machine.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name,
                                                      user=user_name)

    @privileged
    def get_machine_stats(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                          lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[DockerMachineStats], None, None]:
        """Return information of the specified device in a specified network scenario.

         Args:
            machine_name (str): The name of the device for which statistics are requested.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[Optional[DockerMachineStats], None, None]: A generator containing the DockerMachineStats object
            with the device info. Returns None if the device is not found.

        Raises:
            InvocationError: If a running network scenario hash, name or object is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)

        machines_stats = self.get_machines_stats(lab_hash=lab_hash, lab_name=lab_name, lab=lab,
                                                 machine_name=machine_name, all_users=all_users)
        machines_stats_next = next(machines_stats)
        if machines_stats_next:
            (_, machine_stats) = machines_stats_next.popitem()
            yield machine_stats
        else:
            yield None

    def get_machine_stats_obj(self, machine: Machine, all_users: bool = False) \
            -> Generator[Optional[DockerMachineStats], None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine (Machine): The device for which statistics are requested.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[Optional[IMachineStats], None, None]: A generator containing the IMachineStats object
            with the device info. Returns None if the device is not found.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        return self.get_machine_stats(machine.name, lab=machine.lab, all_users=all_users)

    @privileged
    def get_links_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                        link_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, DockerLinkStats], None, None]:
        """Return information about deployed networks.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
           link_name (str): If specified return all the networks with link_name.
           all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, DockerLinkStats], None, None]: A generator containing dicts that has API Object
                identifier as keys and DockerLinksStats objects as values.

        Raises:
            InvocationError: If a running network scenario hash, name or object is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.docker_link.get_links_stats(lab_hash=lab_hash, link_name=link_name, user=user_name)

    @privileged
    def get_link_stats(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[DockerLinkStats], None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link_name (str): The name of the collision domain for which statistics are requested.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
            Generator[Optional[DockerLinkStats], None, None]: A generator containing the DockerLinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        links_stats = self.get_links_stats(lab_hash=lab_hash, link_name=link_name, all_users=all_users)
        links_stats_next = next(links_stats)
        if links_stats_next:
            (_, link_stats) = links_stats_next.popitem()
            yield link_stats
        else:
            yield None

    def get_link_stats_obj(self, link: Link, all_users: bool = False) \
            -> Generator[Optional[DockerLinkStats], None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link (Link): The collision domain for which statistics are requested.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
            Generator[Optional[ILinkStats], None, None]: A generator containing the ILinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        if not link.lab:
            raise LabNotFoundError(f"Link `{link.name}` is not associated to a network scenario.")

        return self.get_link_stats(link.name, lab=link.lab, all_users=all_users)

    @privileged
    def check_image(self, image_name: str) -> None:
        """Check if the specified image is valid.

        Args:
            image_name (str): The name of the image

        Returns:
            None

        Raises:
            ConnectionError: If the image is not locally available and there is no connection to a remote image repository.
            DockerImageNotFoundError: If the image is not found.
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
