import io
import logging
import os
from typing import Set, Dict, Generator, Tuple, List, Optional, Union

from .PodmanPlugin import PodmanPlugin
from .libpod_compat import LibpodCompat
import podman.domain.containers
import podman.domain.networks
from podman import PodmanClient
from podman.client import get_runtime_dir
from podman.errors import APIError, PodmanError
from requests.exceptions import ConnectionError as RequestsConnectionError

from .PodmanImage import PodmanImage
from .PodmanLink import PodmanLink
from .PodmanMachine import PodmanMachine, get_container_ifaces
from .rootless import not_supported_in_rootless
from .exec_stream.PodmanExecStream import PodmanExecStream
from .stats.PodmanLinkStats import PodmanLinkStats
from .stats.PodmanMachineStats import PodmanMachineStats
from ... import utils
from ...decorators import privileged
from ...exceptions import ContainerEngineConnectionError, LinkNotFoundError, MachineCollisionDomainError, \
    InvocationError, LabNotFoundError, MachineNotRunningError, NotSupportedError
from ...exceptions import MachineNotFoundError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.Link import Link
from ...model.Machine import Machine
from ...setting.Setting import Setting
from ...types import SharedCollisionDomainsOption
from ...utils import pack_files_for_tar, check_required_single_not_none_var, check_single_not_none_var

def default_podman_socket() -> str:
    """Return the default Podman service socket URL: the current user's rootless socket under the XDG runtime
    directory. The rootful system socket is never used, since the Podman manager is rootless only.

    Returns:
        str: A `unix://` URL pointing to the Podman service socket.
    """
    return f"unix://{os.path.join(get_runtime_dir(), 'podman', 'podman.sock')}"


def check_podman_status(method):
    """Decorator function to check if the Podman service is running properly."""

    @privileged
    def check_podman(*args, **kw):
        # Call the constructor first
        method(*args, **kw)

        # Client is initialized after constructor call
        client = args[0].client

        try:
            if not client.ping():
                raise ContainerEngineConnectionError(
                    "The Podman service did not respond. Make sure it is running "
                    "(e.g. `systemctl --user enable --now podman.socket`)."
                )
        except (RequestsConnectionError, PodmanError, APIError) as e:
            raise ContainerEngineConnectionError(str(e))

        # Only once the service answers: installing the plugin restarts it.
        PodmanPlugin().check_and_download_plugin()

    return check_podman


class PodmanManager(IManager):
    """The class responsible to interact between Kathara and the Podman APIs."""
    __slots__ = ['client', 'podman_image', 'podman_machine', 'podman_link']

    @check_podman_status
    def __init__(self) -> None:
        # Checked first: as root, the user's socket, plugin directory and Podman configuration do not resolve,
        # and nothing must be installed or created in root's home.
        if utils.is_admin():
            raise NotSupportedError("The Podman manager runs rootless: run Kathara as your normal user, without sudo.")

        base_url = Setting.get_instance().api_socket_url or default_podman_socket()
        try:
            self.client: PodmanClient = PodmanClient(base_url=base_url, timeout=None,
                                                      max_pool_size=utils.get_pool_size())
        except PodmanError as e:
            raise ContainerEngineConnectionError(str(e))
        self.podman_image: PodmanImage = PodmanImage(self.client)
        self.podman_machine: PodmanMachine = PodmanMachine(self.client, self.podman_image)
        self.podman_link: PodmanLink = PodmanLink(self.client)

    @privileged
    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            NotSupportedError: If the device requires privileged mode.
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        # Checked before deploying anything (links included), so a lab is never left half deployed
        # when Kathará is used as a library (the CLI has its own, earlier check for this).
        if machine.is_privileged():
            not_supported_in_rootless("Privileged devices")

        machine.check()

        self.podman_link.deploy_links(machine.lab, selected_links={x.link.name for x in machine.interfaces.values()})
        self.podman_machine.deploy_machines(machine.lab, selected_machines={machine.name})

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

        self.podman_link.deploy_links(link.lab, selected_links={link.name})

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
            NotSupportedError: If any of the devices to deploy requires privileged mode.
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

        if selected_machines:
            machines_to_deploy = {k: v for k, v in lab.machines.items() if k in selected_machines}
        elif excluded_machines:
            machines_to_deploy = {k: v for k, v in lab.machines.items() if k not in excluded_machines}
        else:
            machines_to_deploy = lab.machines

        # Checked before deploying anything (links included), so a lab is never left half deployed
        # when Kathará is used as a library (the CLI has its own, earlier check for this).
        if any(machine.is_privileged() for machine in machines_to_deploy.values()):
            not_supported_in_rootless("Privileged devices")

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
        self.podman_link.deploy_links(lab, selected_links=selected_links, excluded_links=excluded_links)

        # Deploy all lab machines.
        self.podman_machine.deploy_machines(
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
        if LibpodCompat.container_status(machine.api_object) != "running":
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
            if not machine.interfaces or machine.meta['bridged_iface'] > max(machine.interfaces.keys()):
                iface_number = machine.meta['bridged_iface'] + 1
            else:
                iface_number = max(machine.interfaces.keys()) + 1

        interface = machine.add_interface(link, mac_address=mac_address, number=iface_number)

        self.deploy_link(link)
        self.podman_machine.connect_interface(machine, interface)

    @privileged
    def disconnect_machine_from_link(self, machine: Machine, link: Link, keep_link: bool = False) -> None:
        """Disconnect a running Kathara device from a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): The Kathara collision domain from which disconnect the running device.
            keep_link (bool): Keep collision domain. Default: False.

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
        if LibpodCompat.container_status(machine.api_object) != "running":
            raise MachineNotRunningError(machine.name)

        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        if machine.name not in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{machine.name}` is not connected to collision domain `{link.name}`."
            )

        machine.remove_interface(link)

        self.podman_machine.disconnect_from_link(machine, link)
        if not keep_link:
            self.undeploy_link(link)

    @privileged
    def undeploy_machine(self, machine: Machine, keep_links: bool = False) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            keep_links (bool): Keep device's collision domains when undeploying. Default: False.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        self.podman_machine.undeploy(machine.lab.hash, selected_machines={machine.name})
        if not keep_links:
            self.podman_link.undeploy(
                machine.lab.hash, selected_links={x.link.name for x in machine.interfaces.values()}
            )

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

        self.podman_link.undeploy(link.lab.hash, selected_links={link.name})

    @privileged
    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                     selected_machines: Optional[Set[str]] = None,
                     excluded_machines: Optional[Set[str]] = None,
                     selected_links: Optional[Set[str]] = None) -> None:
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
            selected_links (Optional[Set[str]]): If not None, undeploy only the specified collision domains.

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

        self.podman_machine.undeploy(lab_hash, selected_machines=selected_machines, excluded_machines=excluded_machines)

        self.podman_link.undeploy(lab_hash, selected_links=selected_links)

    @privileged
    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        If multiuser scenarios are active, undeploy only current user devices.

        Args:
            all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
                running network scenarios of all users.

        Returns:
            None

        Raises:
            NotSupportedError: If all_users is True.
        """
        if all_users:
            not_supported_in_rootless("Wiping the devices of all users")

        user_name = utils.get_current_user_name() if not all_users else None

        self.podman_machine.wipe(user=user_name)
        self.podman_link.wipe(user=user_name)

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

        self.podman_machine.connect(lab_hash=lab_hash,
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
             stream: bool = True) -> Union[PodmanExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine_name (str): The name of the device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab_name should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a PodmanExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[PodmanExecStream, Tuple[bytes, bytes, int]]: A PodmanExecStream object or
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
        return self.podman_machine.exec(
            lab_hash, machine_name, command, user=user_name, tty=False, wait=wait, stream=stream
        )

    def exec_obj(self, machine: Machine, command: Union[List[str], str], wait: Union[bool, Tuple[int, float]] = False,
                 stream: bool = True) -> Union[PodmanExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine (Machine): The device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a PodmanExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[PodmanExecStream, Tuple[bytes, bytes, int]]: A PodmanExecStream object or
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

        self.podman_machine.copy_files(machine.api_object,
                                       path="/",
                                       tar_data=tar_data
                                       )

    @privileged
    def retrieve_files(self, machine: Machine, src: str, dst: str) -> None:
        """Copy files from a running device path to the host.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            src (str): The path of the file or folder to copy from the device.
            dst (str): The destination path on the host.

        Returns:
            None
        """
        self.podman_machine.retrieve_files(machine.api_object, src, dst)

    @privileged
    def get_machine_api_object(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                               lab: Optional[Lab] = None, all_users: bool = False) \
            -> podman.domain.containers.Container:
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
            podman.domain.containers.Container: Podman API object of devices.

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
        containers = self.podman_machine.get_machines_api_objects_by_filters(
            lab_hash=lab_hash, machine_name=machine_name, user=user_name
        )
        if containers:
            return containers.pop()

        raise MachineNotFoundError(f"Device `{machine_name}` not found.")

    @privileged
    def get_machines_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                                 lab: Optional[Lab] = None, all_users: bool = False) \
            -> List[podman.domain.containers.Container]:
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
            List[podman.domain.containers.Container]: Podman API objects of devices.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.podman_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

    @privileged
    def get_link_api_object(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                            lab: Optional[Lab] = None, all_users: bool = False) -> podman.domain.networks.Network:
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
            podman.domain.networks.Network: Podman API object of the network.

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
        networks = self.podman_link.get_links_api_objects_by_filters(
            lab_hash=lab_hash, link_name=link_name, user=user_name
        )
        if networks:
            return networks.pop()

        raise LinkNotFoundError(f"Collision Domain `{link_name}` not found.")

    @privileged
    def get_links_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                              lab: Optional[Lab] = None, all_users: bool = False) \
            -> List[podman.domain.networks.Network]:
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
            List[podman.domain.networks.Network]: Podman API objects of networks.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        user_name = utils.get_current_user_name() if not all_users else None
        return self.podman_link.get_links_api_objects_by_filters(lab_hash=lab_hash, user=user_name)

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
            if container.attrs['HostConfig'].get('Memory', 0) > 0:
                device.add_meta("mem", f"{int(container.attrs['HostConfig']['Memory'] / (1024 ** 2))}M")

            for env in container.attrs["Config"].get("Env") or []:
                device.add_meta("env", env)

            # Reconvert ports to the device format
            if container.attrs['HostConfig'].get('PortBindings'):
                for port_info, port_data in container.attrs['HostConfig']['PortBindings'].items():
                    (guest_port, protocol) = port_info.split('/')
                    host_port = port_data[0]["HostPort"]
                    device.meta["ports"][(int(host_port), protocol)] = int(guest_port)

            # Reassign sysctls directly. Podman's HostConfig uses the same "Sysctls" key as Docker's
            # inspect output for compat, even though the create-time payload field is `sysctl`.
            device.meta["sysctls"] = container.attrs["HostConfig"].get("Sysctls") or {}

            if "bridged_iface" in container.labels:
                device.add_meta("bridged", True)
                device.add_meta("bridged_iface", int(container.labels['bridged_iface']))

            # Native libpod network-attachment data has no equivalent of Docker's endpoint DriverOpts:
            # interface number, link name and MAC are read back from the `kathara-eth<N>` network
            # alias instead (see PodmanMachine.get_container_ifaces).
            ifaces = get_container_ifaces(container, lab_networks)
            for link_name, iface_info in sorted(ifaces.items(), key=lambda item: item[1]["num"]):
                link = reconstructed_lab.get_or_new_link(link_name)
                link.api_object = iface_info["network"]
                device.add_interface(link, mac_address=iface_info.get("mac_address"), number=iface_info["num"])

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
            map(lambda x: (x.attrs["labels"]["name"], x), deployed_networks.values())
        )

        for container in running_containers:
            container.reload()
            device = lab.get_or_new_machine(container.labels["name"])
            device.api_object = container

            # Collision domains declared in the network scenario
            static_links = set([x.link for x in device.interfaces.values()])

            # Native libpod network-attachment data has no equivalent of Docker's endpoint DriverOpts:
            # interface number, link name and MAC are read back from the `kathara-eth<N>` network
            # alias instead (see PodmanMachine.get_container_ifaces).
            ifaces = get_container_ifaces(container, deployed_networks)

            # Collision domains currently attached to the device
            current_links = set()
            current_ifaces = {}
            for link_name, iface_info in sorted(ifaces.items(), key=lambda item: item[1]["num"]):
                link = lab.get_or_new_link(link_name)
                current_links.add(link)
                current_ifaces[link.name] = iface_info

            # Collision domains attached at runtime to the device
            dynamic_links = current_links - static_links
            # Static collision domains detached at runtime from the device
            deleted_links = static_links - current_links

            for link in static_links:
                if link.name in deployed_networks_by_link_name:
                    link.api_object = deployed_networks_by_link_name[link.name]

            for link in dynamic_links:
                link.api_object = deployed_networks_by_link_name[link.name]
                iface_info = current_ifaces[link.name]
                device.add_interface(link, mac_address=iface_info.get("mac_address"), number=iface_info["num"])

            for link in deleted_links:
                device.remove_interface(link)

    @privileged
    def get_machines_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                           lab: Optional[Lab] = None, machine_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, PodmanMachineStats], None, None]:
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
              Generator[Dict[str, PodmanMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and PodmanMachineStats objects as values.

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
        return self.podman_machine.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name,
                                                       user=user_name)

    @privileged
    def get_machine_stats(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                          lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[PodmanMachineStats], None, None]:
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
            Generator[Optional[PodmanMachineStats], None, None]: A generator containing the PodmanMachineStats object
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
            -> Generator[Optional[PodmanMachineStats], None, None]:
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
            -> Generator[Dict[str, PodmanLinkStats], None, None]:
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
             Generator[Dict[str, PodmanLinkStats], None, None]: A generator containing dicts that has API Object
                identifier as keys and PodmanLinkStats objects as values.

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
        return self.podman_link.get_links_stats(lab_hash=lab_hash, link_name=link_name, user=user_name)

    @privileged
    def get_link_stats(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[PodmanLinkStats], None, None]:
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
            Generator[Optional[PodmanLinkStats], None, None]: A generator containing the PodmanLinkStats object
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
            -> Generator[Optional[PodmanLinkStats], None, None]:
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
        self.podman_image.check(image_name)

    @privileged
    def get_release_version(self) -> str:
        """Return the current manager version.

        Returns:
            str: The current manager version.
        """
        # Unlike Docker's flat `{"Version": "24.0.0", ...}`, libpod's native /version reports a
        # nested `{"Version": {"Version": "4.9.3", "APIVersion": ..., ...}, "Platform": {...}}`.
        version = self.client.version().get("Version")
        return version.get("Version") if isinstance(version, dict) else version

    @staticmethod
    def get_formatted_manager_name() -> str:
        """Return a formatted string containing the current manager name.

        Returns:
            str: A formatted string containing the current manager name.
        """
        return "Podman (Kathara)"
