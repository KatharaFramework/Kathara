import io
from abc import ABC, abstractmethod
from typing import Dict, Set, Any, Generator, Tuple, List, Optional, Union

from .stats.ILinkStats import ILinkStats
from .stats.IMachineStats import IMachineStats
from ...model.Lab import Lab
from ...model.Link import Link
from ...model.Machine import Machine


class IManager(ABC):
    """Interface to be implemented in the virtualization managers"""

    @abstractmethod
    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
        """
        raise NotImplementedError("You must implement `deploy_machine` method.")

    @abstractmethod
    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        raise NotImplementedError("You must implement `deploy_link` method.")

    @abstractmethod
    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Set[str]): If not None, deploy only the specified devices.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `deploy_lab` method.")

    @abstractmethod
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
        raise NotImplementedError("You must implement `connect_machine_to_link` method.")

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
        raise NotImplementedError("You must implement `disconnect_machine_from_link` method.")

    @abstractmethod
    def undeploy_machine(self, machine: Machine) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the device specified is not associated to any network scenario.
        """
        raise NotImplementedError("You must implement `undeploy_machine` method.")

    @abstractmethod
    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain is not associated to any network scenario.
        """
        raise NotImplementedError("You must implement `undeploy_link` method.")

    @abstractmethod
    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                     selected_machines: Optional[Set[str]] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        raise NotImplementedError("You must implement `undeploy_lab` method.")

    @abstractmethod
    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        Args:
            all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
                running network scenarios of all users.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `wipe` method.")

    @abstractmethod
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
        raise NotImplementedError("You must implement `connect_tty` method.")

    @abstractmethod
    def exec(self, machine_name: str, command: Union[List[str], str], lab_hash: Optional[str] = None,
             lab_name: Optional[str] = None, lab: Optional[Lab] = None, wait: Union[bool, Tuple[int, float]] = False) \
            -> Generator[Tuple[bytes, bytes], None, None]:
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

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        raise NotImplementedError("You must implement `exec` method.")

    @abstractmethod
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, io.IOBase]): A dict containing the device path as key and
                fileobj to copy in path as value.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `copy_files` method.")

    @abstractmethod
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
        raise NotImplementedError("You must implement `get_machine_api_object` method.")

    @abstractmethod
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
        """
        raise NotImplementedError("You must implement `get_machines_api_objects` method.")

    @abstractmethod
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
        raise NotImplementedError("You must implement `get_link_api_object` method.")

    @abstractmethod
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
        """
        raise NotImplementedError("You must implement `get_links_api_objects` method.")

    @abstractmethod
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
        raise NotImplementedError("You must implement `get_lab_from_api` method.")

    @abstractmethod
    def update_lab_from_api(self, lab: Lab) -> None:
        """Update the passed network scenario from API objects.

        Args:
            lab (Lab): The network scenario to update.
        """
        raise NotImplementedError("You must implement `update_lab_from_api` method.")

    @abstractmethod
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
        """
        raise NotImplementedError("You must implement `get_machines_stats` method.")

    @abstractmethod
    def get_machine_stats(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                          lab: Optional[Lab] = None, all_users: bool = False) -> Generator[IMachineStats, None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine_name (str): The device name.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            IMachineStats: IMachineStats object containing the device info.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        raise NotImplementedError("You must implement `get_machine_stats` method.")

    @abstractmethod
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
        """
        raise NotImplementedError("You must implement `get_links_stats` method.")

    @abstractmethod
    def get_link_stats(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None, all_users: bool = False) -> Generator[ILinkStats, None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link_name (str): If specified return all the networks with link_name.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, ILinkStats], None, None]: A generator containing dicts that has API Object
             identifier as keys and ILinksStats objects as values.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        raise NotImplementedError("You must implement `get_link_stats` method.")

    @abstractmethod
    def check_image(self, image_name: str) -> None:
        """Check if the specified image is valid.

        Args:
            image_name (str): The name of the image

        Returns:
            None

        Raises:
            ConnectionError: If the image is not locally available and there is no connection to a remote image repository.
            ImageNotFoundError: If the image is not found.
        """
        raise NotImplementedError("You must implement `check_image` method.")

    @abstractmethod
    def get_release_version(self) -> str:
        """Return the current manager version.

        Returns:
            str: The current manager version.
        """
        raise NotImplementedError("You must implement `get_release_version` method.")

    @staticmethod
    def get_formatted_manager_name() -> str:
        """Return a formatted string containing the current manager name.

        Returns:
            str: A formatted string containing the current manager name.
        """
        raise NotImplementedError("You must implement `get_formatted_manager_name` method.")
