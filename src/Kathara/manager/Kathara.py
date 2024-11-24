from __future__ import annotations

import io
from typing import Set, Dict, Generator, Any, Tuple, List, Optional, Union

from ..exceptions import InstantiationError
from ..foundation.manager.IManager import IManager
from ..foundation.manager.ManagerFactory import ManagerFactory
from ..foundation.manager.exec_stream.IExecStream import IExecStream
from ..foundation.manager.stats.ILinkStats import ILinkStats
from ..foundation.manager.stats.IMachineStats import IMachineStats
from ..model.Lab import Lab
from ..model.Link import Link
from ..model.Machine import Machine
from ..setting.Setting import Setting, AVAILABLE_MANAGERS


class Kathara(IManager):
    """Facade class for interacting with Kathara. It is a proxy for the selected Manager."""
    __slots__ = ['manager']

    __instance: Kathara = None

    @staticmethod
    def get_instance() -> Kathara:
        """Get an instance of Kathara.
    
        Returns:
            Kathara: instance of Kathara.

        Raises:
            InstantiationError: If two instances of the class are created.
        """
        if Kathara.__instance is None:
            Kathara()

        return Kathara.__instance

    def __init__(self) -> None:
        if Kathara.__instance is not None:
            raise InstantiationError("This class is a singleton!")
        else:
            manager_type = Setting.get_instance().manager_type

            self.manager: IManager = ManagerFactory().create_instance(module_args=(manager_type,),
                                                                      class_args=(manager_type.capitalize(),)
                                                                      )

            Kathara.__instance = self

    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
        """
        self.manager.deploy_machine(machine)

    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        self.manager.deploy_link(link)

    def deploy_lab(self, lab: Lab, selected_machines: Optional[Set[str]] = None,
                   excluded_machines: Optional[Set[str]] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Optional[Set[str]]): If not None, deploy only the specified devices.
            excluded_machines (Optional[Set[str]]): If not None, exclude devices from being deployed.

        Returns:
            None
        """
        self.manager.deploy_lab(lab, selected_machines, excluded_machines)

    def connect_machine_to_link(self, machine: Machine, link: Link, mac_address: Optional[str] = None) -> None:
        """Connect a Kathara device to a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): A Kathara collision domain object.
            mac_address (Optional[str]): The MAC address to assign to the interface.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            MachineCollisionDomainConflictError: If the device is already connected to the collision domain.
        """
        self.manager.connect_machine_to_link(machine, link, mac_address)

    def disconnect_machine_from_link(self, machine: Machine, link: Link) -> None:
        """Disconnect a Kathara device from a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): The Kathara collision domain from which disconnect the device.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
            LabNotFoundError: If the collision domain is not associated to any network scenario.
            MachineCollisionDomainConflictError: If the device is not connected to the collision domain.
        """
        self.manager.disconnect_machine_from_link(machine, link)

    def undeploy_machine(self, machine: Machine) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
        """
        self.manager.undeploy_machine(machine)

    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        self.manager.undeploy_link(link)

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
            InvocationError: If a running network scenario hash or name is not specified.
        """
        self.manager.undeploy_lab(lab_hash, lab_name, lab, selected_machines, excluded_machines)

    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        Args:
            all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
                running network scenarios of all users.

        Returns:
            None
        """
        self.manager.wipe(all_users)

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
        self.manager.connect_tty(machine_name, lab_hash, lab_name, lab, shell, logs, wait)

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
        self.manager.connect_tty_obj(machine, shell, logs, wait)

    def exec(self, machine_name: str, command: Union[List[str], str], lab_hash: Optional[str] = None,
             lab_name: Optional[str] = None, lab: Optional[Lab] = None, wait: Union[bool, Tuple[int, float]] = False,
             stream: bool = True) -> Union[IExecStream, Tuple[bytes, bytes, int]]:
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
           stream (bool): If True, return an IExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[IExecStream, Tuple[bytes, bytes, int]]: An IExecStream object or
            a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
        """
        return self.manager.exec(machine_name, command, lab_hash, lab_name, lab, wait, stream)

    def exec_obj(self, machine: Machine, command: Union[List[str], str], wait: Union[bool, Tuple[int, float]] = False,
                 stream: bool = True) -> Union[IExecStream, Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine (Machine): The device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return an IExecStream object. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[IExecStream, Tuple[bytes, bytes, int]]: An IExecStream object or
            a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
        """
        return self.manager.exec_obj(machine, command, wait, stream)

    def copy_files(self, machine: Machine, guest_to_host: Dict[str, Union[str, io.IOBase]]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, Union[str, io.IOBase]]): A dict containing the device path as key and a
                fileobj to copy in path as value or a path to a file.

        Returns:
            None
        """
        self.manager.copy_files(machine, guest_to_host)

    def get_machine_api_object(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                               lab: Optional[Lab] = None, all_users: bool = False) -> Any:
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
            Any: API object of the device specific for the current manager.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotFoundError: If the specified device is not found.
        """
        return self.manager.get_machine_api_object(machine_name, lab_hash, lab_name, lab, all_users)

    def get_machines_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                                 lab: Optional[Lab] = None, all_users: bool = False) -> List[Any]:
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
            List[Any]: API objects of devices, specific for the current manager.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        return self.manager.get_machines_api_objects(lab_hash, lab_name, lab, all_users)

    def get_link_api_object(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                            lab: Optional[Lab] = None, all_users: bool = False) -> Any:
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
            Any: API object of the collision domain specific for the current manager.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            LinkNotFoundError: If the collision domain is not found.
        """
        return self.manager.get_link_api_object(link_name, lab_hash, lab_name, lab, all_users)

    def get_links_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                              lab: Optional[Lab] = None, all_users: bool = False) -> List[Any]:
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
            List[Any]: API objects of collision domains, specific for the current manager.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        return self.manager.get_links_api_objects(lab_hash, lab_name, lab, all_users)

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
        return self.manager.get_lab_from_api(lab_hash, lab_name)

    def update_lab_from_api(self, lab: Lab) -> None:
        """Update the passed network scenario from API objects.

        Args:
            lab (Lab): The network scenario to update.
        """
        self.manager.update_lab_from_api(lab)

    def get_machines_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                           lab: Optional[Lab] = None, machine_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, IMachineStats], None, None]:
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
              Generator[Dict[str, IMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and IMachineStats objects as values.

        Raises:
            InvocationError: If more than one param among lab_hash, lab_name and lab is specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        return self.manager.get_machines_stats(lab_hash, lab_name, lab, machine_name, all_users)

    def get_machine_stats(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                          lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[IMachineStats], None, None]:
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
            Generator[Optional[IMachineStats], None, None]: A generator containing the IMachineStats object
            with the device info. Returns None if the device is not found.

        Raises:
            InvocationError: If more than one param among lab_hash, lab_name and lab is specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        return self.manager.get_machine_stats(machine_name, lab_hash, lab_name, lab, all_users)

    def get_machine_stats_obj(self, machine: Machine, all_users: bool = False) \
            -> Generator[Optional[IMachineStats], None, None]:
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
        return self.manager.get_machine_stats_obj(machine, all_users)

    def get_links_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                        link_name: str = None, all_users: bool = False) -> Generator[Dict[str, ILinkStats], None, None]:
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
             Generator[Dict[str, ILinkStats], None, None]: A generator containing dicts that has API Object
             identifier as keys and ILinksStats objects as values.

        Raises:
            InvocationError: If a running network scenario hash, name or object is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        return self.manager.get_links_stats(lab_hash, lab_name, lab, link_name, all_users)

    def get_link_stats(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[ILinkStats], None, None]:
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
            Generator[Optional[ILinkStats], None, None]: A generator containing the ILinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            PrivilegeError: If all_users is True and the user does not have root privileges.
        """
        return self.manager.get_link_stats(link_name, lab_hash, lab_name, lab, all_users)

    def get_link_stats_obj(self, link: Link, all_users: bool = False) -> Generator[Optional[ILinkStats], None, None]:
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
        return self.manager.get_link_stats_obj(link, all_users)

    def check_image(self, image_name: str) -> None:
        """Check if the specified image is valid.

        Args:
            image_name (str): The name of the image

        Returns:
            None

        Raises:
            ConnectionError: If the image is not locally available and there is no connection to a
                remote image repository.
            ImageNotFoundError: If the image is not found.
        """
        self.manager.check_image(image_name)

    def get_release_version(self) -> str:
        """Return the current manager version.

        Returns:
            str: The current manager version.
        """
        return self.manager.get_release_version()

    def get_formatted_manager_name(self) -> str:
        """Return a formatted string containing the current manager name.

        Returns:
            str: A formatted string containing the current manager name.
        """
        return self.manager.get_formatted_manager_name()

    @staticmethod
    def get_available_managers_name() -> Dict[str, str]:
        """Return a dict containing the available manager names.

        Returns:
            Dict[str, str]: keys are the manager names, values are the formatted manager names.
        """
        managers = {}
        manager_factory = ManagerFactory()

        for manager_name in AVAILABLE_MANAGERS:
            manager = manager_factory.get_class(module_args=(manager_name,),
                                                class_args=(manager_name.capitalize(),)
                                                )

            managers[manager_name] = manager.get_formatted_manager_name()

        return managers
