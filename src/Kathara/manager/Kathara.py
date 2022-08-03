from __future__ import annotations

import io
from typing import Set, Dict, Generator, Any, Tuple, List, Optional

from ..foundation.manager.IManager import IManager
from ..foundation.manager.ManagerFactory import ManagerFactory
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
        """
        if Kathara.__instance is None:
            Kathara()

        return Kathara.__instance

    def __init__(self) -> None:
        if Kathara.__instance is not None:
            raise Exception("This class is a singleton!")
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
        """
        self.manager.deploy_machine(machine)

    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        self.manager.deploy_link(link)

    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Set[str]): If not None, deploy only the specified devices.

        Returns:
            None
        """
        self.manager.deploy_lab(lab, selected_machines)

    def update_lab(self, lab: Lab) -> None:
        """Update a running network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.

        Returns:
            None
        """
        self.manager.update_lab(lab)

    def undeploy_machine(self, machine: Machine) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None
        """
        self.manager.undeploy_machine(machine)

    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        self.manager.undeploy_link(link)

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
        self.manager.undeploy_lab(lab_hash, lab_name, selected_machines)

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
        self.manager.connect_tty(machine_name, lab_hash, lab_name, shell, logs)

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
        return self.manager.exec(machine_name, command, lab_hash, lab_name)

    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, io.IOBase]): A dict containing the device path as key and
                fileobj to copy in path as value.

        Returns:
            None
        """
        self.manager.copy_files(machine, guest_to_host)

    def get_machine_api_object(self, machine_name: str, lab_hash: str = None, lab_name: str = None,
                               all_users: bool = False) -> Any:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            machine_name (str): The name of the device.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_hash should be set.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            Any: API object of the device specific for the current manager.
        """
        return self.manager.get_machine_api_object(machine_name, lab_hash, lab_name, all_users)

    def get_machines_api_objects(self, lab_hash: str = None, lab_name: str = None, all_users: bool = False) \
            -> List[Any]:
        """Return API objects of running devices.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            List[Any]: API objects of devices, specific for the current manager.
        """
        return self.manager.get_machines_api_objects(lab_hash, lab_name, all_users)

    def get_link_api_object(self, link_name: str, lab_hash: str = None, lab_name: str = None,
                            all_users: bool = False) -> Any:
        """Return the corresponding API object of a collision domain in a network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_hash should be set.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            Any: API object of the collision domain specific for the current manager.
        """
        return self.manager.get_link_api_object(link_name, lab_hash, lab_name, all_users)

    def get_links_api_objects(self, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> List[Any]:
        """Return API objects of collision domains in a network scenario.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            List[Any]: API objects of collision domains, specific for the current manager.
        """
        return self.manager.get_links_api_objects(lab_hash, lab_name, all_users)

    def get_machines_stats(self, lab_hash: str = None, lab_name: str = None, machine_name: str = None,
                           all_users: bool = False) -> Generator[Dict[str, IMachineStats], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
            machine_name (str): If specified return all the devices with machine_name.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, IMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and IMachineStats objects as values.
        """
        return self.manager.get_machines_stats(lab_hash, lab_name, machine_name, all_users)

    def get_machine_stats(self, machine_name: str, lab_hash: str = None,
                          lab_name: str = None, all_users: bool = False) -> Generator[IMachineStats, None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine_name (str): The device name.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
                If None, lab_hash should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            IMachineStats: IMachineStats object containing the device info.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        return self.manager.get_machine_stats(machine_name, lab_hash, lab_name, all_users)

    def get_links_stats(self, lab_hash: str = None, lab_name: str = None, link_name: str = None,
                        all_users: bool = False) -> Generator[Dict[str, ILinkStats], None, None]:
        """Return information about deployed networks.

        Args:
           lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
           lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
           link_name (str): If specified return all the networks with link_name.
           all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, ILinkStats], None, None]: A generator containing dicts that has API Object
             identifier as keys and ILinksStats objects as values.
        """
        return self.manager.get_links_stats(lab_hash, lab_name, link_name, all_users)

    def get_link_stats(self, link_name: str, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> \
            Generator[ILinkStats, None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
           link_name (str): If specified return all the networks with link_name.
           lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
           lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
                If None, lab_hash should be set.
           all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, ILinkStats], None, None]: A generator containing dicts that has API Object
             identifier as keys and ILinksStats objects as values.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        return self.manager.get_link_stats(link_name, lab_hash, lab_name, all_users)

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
