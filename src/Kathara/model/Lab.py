import collections
import logging
from itertools import chain
from typing import Dict, Set, Any, List, Union, Optional, Tuple

from fs import open_fs
from fs.base import FS

from . import Interface as InterfacePackage
from . import Link as LinkPackage
from . import Machine as MachinePackage
from .ExternalLink import ExternalLink
from .. import utils
from ..exceptions import LinkNotFoundError, MachineNotFoundError, MachineAlreadyExistsError, LinkAlreadyExistsError
from ..foundation.model.FilesystemMixin import FilesystemMixin

LAB_METADATA: List[str] = ["LAB_NAME", "LAB_DESCRIPTION", "LAB_VERSION", "LAB_AUTHOR", "LAB_EMAIL", "LAB_WEB"]


class Lab(FilesystemMixin):
    """A Kathara network scenario, containing information about devices and collision domains.

    Attributes:
        name (str): The name of the network scenario.
        description (str): A short description of the network scenario.
        version (str): The version of the network scenario.
        author (str): The author of the network scenario.
        email (str): The email of the author of the network scenario.
        web (str): The web address of the author of the network scenario.
        hash (str): The hash identifier of the network scenario.
        machines (Dict[str, Kathara.model.Machine]): The devices of the network scenario. Keys are device names, Values
            are Kathara device objects.
        links (Dict[str, Kathara.model.Link]): The collision domains of the network scenario.
            Keys are collision domains names, Values are Kathara collision domain objects.
        general_options (Dict[str, Any]): The general options of the network scenario.
        global_machine_metadata (Dict[str, Any]): Metadata to apply to all the devices of the network scenario at
            the startup.
        has_dependencies (bool): True if there are dependencies among the devices boot.
        shared_path (str): Path to shared folder of the network scenario, if the network scenario has a real OS path.
        fs (fs.FS): The filesystem of the network scenario. Contains files and configurations associated to it.
    """
    __slots__ = ['_name', 'description', 'version', 'author', 'email', 'web', 'hash',
                 'machines', 'links', 'general_options', 'global_machine_metadata', 'has_dependencies', 'shared_path']

    def __init__(self, name: Optional[str], path: Optional[str] = None) -> None:
        """Create a new instance of a Kathara network scenario.

        Args:
            name (str): The name of the network scenario.
            path (str): The path to the network scenario directory, if exists.

        Returns:
            None
        """
        super().__init__()

        self._name: Optional[str] = name
        self.description: Optional[str] = None
        self.version: Optional[str] = None
        self.author: Optional[str] = None
        self.email: Optional[str] = None
        self.web: Optional[str] = None

        self.machines: Dict[str, 'MachinePackage.Machine'] = {}
        self.links: Dict[str, 'LinkPackage.Link'] = {}

        self.general_options: Dict[str, Any] = {
            'privileged_machines': False,
        }

        self.global_machine_metadata: Dict[str, Any] = {}

        self.has_dependencies: bool = False

        self.shared_path: Optional[str] = None

        self.hash: str = utils.generate_urlsafe_hash(path if self._name is None else self._name)

        if path:
            self.fs: FS = open_fs(f"osfs://{path}")
        else:
            self.fs: FS = open_fs("mem://")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.hash = utils.generate_urlsafe_hash(value)

    def connect_machine_to_link(self, machine_name: str, link_name: str,
                                machine_iface_number: int = None, mac_address: Optional[str] = None) \
            -> Tuple['MachinePackage.Machine', 'InterfacePackage.Interface']:
        """Connect the specified device to the specified collision domain.

        Args:
            machine_name (str): The device name.
            link_name (str): The collision domain name.
            machine_iface_number (int): The number of the device interface to connect. If it is None, the first free
                number is used.
            mac_address (Optional[str]): The MAC address to assign to the interface.

        Returns:
            Tuple[Kathara.model.Machine.Machine, Kathara.model.Interface.Interface]: A tuple containing the Kathara
                device and the interface object specified by their names.

        Raises:
            Exception: If an already used interface number is specified.
        """
        machine = self.get_or_new_machine(machine_name)
        link = self.get_or_new_link(link_name)

        interface = machine.add_interface(link, number=machine_iface_number, mac_address=mac_address)

        return machine, interface

    def connect_machine_obj_to_link(self, machine: 'MachinePackage.Machine', link_name: str,
                                    machine_iface_number: int = None, mac_address: Optional[str] = None) \
            -> 'InterfacePackage.Interface':
        """Connect the specified device object to the specified collision domain.

        Args:
            machine (Kathara.model.Machine): The device object.
            link_name (str): The collision domain name.
            machine_iface_number (int): The number of the device interface to connect. If it is None, the first free
                number is used.

        Returns:
            Kathara.model.Interface.Interface: The interface object associated to the new interface..

        Raises:
            Exception: If an already used interface number is specified.
        """
        link = self.get_or_new_link(link_name)

        interface = machine.add_interface(link, number=machine_iface_number, mac_address=mac_address)

        return interface

    def assign_meta_to_machine(self, machine_name: str, meta_name: str, meta_value: str) -> Optional[Any]:
        """Assign meta information to the specified device.

        Args:
            machine_name (str): The name of the device.
            meta_name (str): The name of the meta property.
            meta_value (str): The value of the meta property.

        Returns:
            Optional[Any]: Previous value if meta was already assigned, None otherwise.

        Raises:
            MachineOptionError: If invalid values are specified for meta properties.
        """
        machine = self.get_or_new_machine(machine_name)

        return machine.add_meta(meta_name, meta_value)

    def attach_external_links(self, external_links: Dict[str, List[ExternalLink]]) -> None:
        """Attach external collision domains to the network scenario.

        Args:
            external_links (Dict[Kathara.model.Link, List[Kathara.model.ExternalLink]]): Keys are Link objects,
            values are ExternalLink objects.

        Returns:
            None

        Raises:
            LinkNotFoundError: If the external collision domain specified is not associated to the network scenario.
        """
        for (link_name, link_external_links) in external_links.items():
            if link_name not in self.links:
                raise LinkNotFoundError("Collision domain `%s` (declared in lab.ext) not found in network scenario "
                                        "collision domains." % link_name)

            self.links[link_name].external += link_external_links

    def check_integrity(self) -> None:
        """Check if the network interfaces numbers of all the devices in the network scenario are correctly assigned.

        Returns:
            None

        Raises:
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
        """
        logging.debug("Checking network scenario integrity...")

        for machine in self.machines.values():
            machine.check()

    def get_links_from_machines(self, machines: Union[List[str], Set[str]]) -> Set[str]:
        """Return the name of the collision domains connected to the devices.

        Args:
            machines (Union[List[str], Set[str]]): A set or a list with selected devices names.

        Returns:
            Set[str]: A set of names of collision domains.
        """
        # Intersect selected machines names with self.machines keys
        machines = set(self.machines.keys()) & set(machines)
        # Apply filtering
        machines = [v for (k, v) in self.machines.items() if k in machines]

        # Get only selected machines Link objects.
        selected_links = set(chain.from_iterable([machine.interfaces.values() for machine in machines]))
        selected_links = {interface.link.name for interface in selected_links}

        return selected_links

    def get_links_from_machine_objs(self,
                                    machines: Union[List['MachinePackage.Machine'], Set['MachinePackage.Machine']]) -> \
            Set[str]:
        """Return the name of the collision domains connected to the devices.

        Args:
            machines (Union[List[str], Set[str]]): A set or a list with selected devices names.

        Returns:
            Set[str]: A set of names of collision domains.
        """
        # Intersect selected machines names with self.machines keys
        machines = set(self.machines.keys()) & set(map(lambda x: x.name, machines))
        # Apply filtering
        machines = [v for (k, v) in self.machines.items() if k in machines]

        # Get only selected machines Link objects.
        selected_links = set(chain.from_iterable([machine.interfaces.values() for machine in machines]))
        selected_links = {interface.link.name for interface in selected_links}

        return selected_links

    def apply_dependencies(self, dependencies: List[str]) -> None:
        """Order the list of devices of the network scenario to satisfy the boot dependencies.

        Args:
            dependencies (List[str]): If not empty, dependencies are applied.

        Returns:
            None
        """

        def dep_sort(item: str) -> int:
            try:
                return dependencies.index(item) + 1
            except ValueError:
                return 0

        self.machines = collections.OrderedDict(sorted(self.machines.items(), key=lambda t: dep_sort(t[0])))
        self.has_dependencies = True

    def get_machine(self, name: str) -> 'MachinePackage.Machine':
        """Get the specified device.

        Args:
            name (str): The name of the device

        Returns:
            Kathara.model.Machine: A Kathara device.

        Raises:
            MachineNotFoundError: If the device is not in the network scenario.
        """
        if name not in self.machines:
            raise MachineNotFoundError(f"Device {name} not in the network scenario.")

        return self.machines[name]

    def new_machine(self, name: str, **kwargs) -> 'MachinePackage.Machine':
        """Create and add the device to the devices list.

        Args:
            name (str): The name of the device
            **kwargs: Contains device meta information.
                Keys are meta property names, values are meta property values.

        Returns:
            Kathara.model.Machine: A Kathara device.

        Raises:
            MachineAlreadyExistsError: If the device is already in the network scenario.
        """
        if name in self.machines:
            raise MachineAlreadyExistsError(name)

        self.machines[name] = MachinePackage.Machine(self, name, **kwargs)

        return self.machines[name]

    def get_or_new_machine(self, name: str, **kwargs) -> 'MachinePackage.Machine':
        """Get the specified device. If it not exists, create and add it to the devices list.

        Args:
            name (str): The name of the device
            **kwargs: Contains device meta information.
                Keys are meta property names, values are meta property values.

        Returns:
            Kathara.model.Machine: A Kathara device.
        """
        if name not in self.machines:
            self.machines[name] = MachinePackage.Machine(self, name, **kwargs)

        return self.machines[name]

    def get_link(self, name: str) -> 'LinkPackage.Link':
        """Get the specified collision domain.

        Args:
            name (str): The name of the collision domain.

        Returns:
            Kathara.model.Link: A Kathara collision domain.

        Raises:
            LinkNotFoundError: If the specified link is not in the network scenario.
        """
        if name not in self.links:
            raise LinkNotFoundError(f"Collision domain {name} not found in the network scenario.")

        return self.links[name]

    def new_link(self, name: str) -> 'LinkPackage.Link':
        """Create the collision domain and add it to the collision domains list.

        Args:
            name (str): The name of the collision domain.

        Returns:
            Kathara.model.Link: A Kathara collision domain.

        Raises:
            LinkAlreadyExistsError: If the specified link is already in the network scenario.
        """
        if name in self.links:
            raise LinkAlreadyExistsError(f"Collision domain {name} is already the network scenario.")

        self.links[name] = LinkPackage.Link(self, name)

        return self.links[name]

    def get_or_new_link(self, name: str) -> 'LinkPackage.Link':
        """Get the specified collision domain. If it not exists, create and add it to the collision domains list.

        Args:
            name (str): The name of the collision domain.

        Returns:
            Kathara.model.Link: A Kathara collision domain.
        """
        if name not in self.links:
            self.links[name] = LinkPackage.Link(self, name)

        return self.links[name]

    def create_shared_folder(self) -> None:
        """If the network scenario has a directory, create the network scenario shared folder.

        Returns:
            None

        Raises:
            IOError: If the shared folder is a Symlink, delete it.
            OSError: If there is a permission error.
        """
        if not self.has_host_path():
            return

        try:
            self.shared_path = self.fs.makedir('shared', recreate=True).getsyspath("")
            if self.fs.islink('shared'):
                raise ValueError("`shared` folder is a symlink, delete it.")
        except OSError:
            # Do not create shared folder if not permitted.
            return

    def has_host_path(self) -> bool:
        """Check if the network scenario has a directory on the host.

        Returns:
            bool: True if network scenario has a path on the host filesystem, else False.
        """
        return self.fs_type() == "os"

    def add_option(self, name: str, value: Any) -> None:
        """Add an option to the network scenario.

        Args:
            name (str): The name of the option.
            value (Any): The value of the option.

        Returns:
            None
        """
        if value is not None:
            self.general_options[name] = value

    def add_global_machine_metadata(self, name: str, value: Any) -> None:
        """Add a global machine metadata to the network scenario.

        Args:
            name (str): The name of the meta.
            value (Any): The value of the meta.

        Returns:
            None
        """
        if value is not None:
            self.global_machine_metadata[name] = value

    def has_machine(self, machine_name: str) -> bool:
        """Check if the specified device is in the network scenario.

        Args:
            machine_name (str): The name of the device to search.

        Returns:
            bool: True if the device is in the network scenario, else False.
        """
        return machine_name in self.machines.keys()

    def has_machines(self, machine_names: Set[str]) -> bool:
        """Check if the specified devices are in the network scenario.

        Args:
            machine_names (Set[str]): A set of strings containing the names of the devices to search.

        Returns:
            bool: True if the devices are all in the network scenario, else False.
        """
        return all(map(lambda x: self.has_machine(x), machine_names))

    def has_link(self, link_name: str) -> bool:
        """Check if the specified collision domain is in the network scenario.

        Args:
            link_name (str): The name of the collision domain to search.

        Returns:
            bool: True if the collision domain is in the network scenario, else False.
        """
        return link_name in self.links.keys()

    def has_links(self, link_names: Set[str]) -> bool:
        """Check if the specified collision domains are in the network scenario.

        Args:
            link_names (Set[str]): A set of strings containing the names of the collision domains to search.

        Returns:
            bool: True if the collision domains are all in the network scenario, else False.
        """
        return all(map(lambda x: self.has_link(x), link_names))

    def __repr__(self) -> str:
        return "Lab(%s, %s, %s, %s)" % (self.fs, self.hash, self.machines, self.links)

    def __str__(self) -> str:
        lab_info = []

        if self._name:
            lab_info.append(f"Name: {self._name}")
        if self.description:
            lab_info.append(f"Description: {self.description}")
        if self.version:
            lab_info.append(f"Version: {self.version}")
        if self.author:
            lab_info.append(f"Author(s): {self.author}")
        if self.email:
            lab_info.append(f"Email: {self.email}")
        if self.web:
            lab_info.append(f"Website: {self.web}")

        return "\n".join(lab_info)
