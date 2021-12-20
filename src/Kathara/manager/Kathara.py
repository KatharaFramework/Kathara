from __future__ import annotations

import io
from typing import Set, Dict, Generator, Any, Tuple, List

from ..foundation.manager.IManager import IManager
from ..foundation.manager.ManagerFactory import ManagerFactory
from ..model.Lab import Lab
from ..model.Machine import Machine
from ..setting.Setting import Setting, AVAILABLE_MANAGERS


class Kathara(IManager):
    """Facade class for interacting with Kathara. It is a proxy for the selected virtualization manager."""
    __slots__ = ['manager']

    __instance: Kathara = None

    @staticmethod
    def get_instance() -> Kathara:
        """Get an instance of the current Kathara Manager.
    
        Returns:
            Kathara: instance of the current Kathara Manager.
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

    def undeploy_lab(self, lab_hash: str, selected_machines: Set[str] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_machines (Set[str]): If not None, undeploy only the specified devices.

        Returns:
            None
        """
        self.manager.undeploy_lab(lab_hash, selected_machines)

    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        Args:
        all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
           running network scenarios of all users.

        Returns:
            None
        """
        self.manager.wipe(all_users)

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
        self.manager.connect_tty(lab_hash, machine_name, shell, logs)

    def exec(self, lab_hash: str, machine_name: str, command: str) -> Generator[Tuple[bytes, bytes], None, None]:
        """Exec a command on a device in a running network scenario.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            machine_name (str): The name of the device to connect.
            command (str): The command to exec on the device.

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.
        """
        return self.manager.exec(lab_hash, machine_name, command)

    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running machine object. It must have the api_object field populated.
            guest_to_host (Dict[str, io.IOBase]): A dict containing the device path as key and
                fileobj to copy in path as value.

        Returns:
            None
        """
        self.manager.copy_files(machine, guest_to_host)

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
        return self.manager.get_lab_info(lab_hash, machine_name, all_users)

    def get_formatted_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> str:
        """Return a formatted string with the information about the running devices.

        Args:
            lab_hash (str): If not None, return information of the corresponding network scenario.
            machine_name (str): If not None, return information of the specified device.
            all_users (bool): If True, return information about the device of all users.

        Returns:
             str: String containing devices info
        """
        return self.manager.get_formatted_lab_info(lab_hash, machine_name, all_users)

    def get_machine_api_object(self, lab_hash: str, machine_name: str) -> Any:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            lab_hash (str): The hash of the network scenario.
            machine_name (str): The name of the device.

        Returns:
            Any: The Api object of the device specific for the current manager.
        """
        return self.manager.get_machine_api_object(lab_hash, machine_name)

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
        return self.manager.get_machine_info(machine_name, lab_hash, all_users)

    def get_formatted_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) -> str:
        """Return formatted information of running devices with a specified name.

        Args:
            machine_name (str): The device name.
            lab_hash (str): If not None, search the device in the specified network scenario.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            str: The formatted devices properties.
        """
        return self.manager.get_formatted_machine_info(machine_name, lab_hash, all_users)

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
