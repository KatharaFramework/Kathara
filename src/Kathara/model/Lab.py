import collections
from itertools import chain
from typing import Dict, Set, Any, List, Union, Optional, Tuple

import fs
from fs.base import FS
from fs.osfs import OSFS

from . import Machine as MachinePackage
from .ExternalLink import ExternalLink
from .Link import Link
from .. import utils
from ..exceptions import LinkNotFoundError, MachineNotFoundError, MachineAlreadyExistsError, LinkAlreadyExistsError


class Lab(object):
    """A Kathara network scenario, containing information about devices and collision domains.

    Attributes:
        name (str): The name of the network scenario.
        description (str): A short description of the network scenario.
        version (str): The version of the network scenario.
        author (str): The author of the network scenario.
        email (str): The email of the author of the network scenario.
        web (str): The web address of the author of the network scenario.
        fs (FS): An object referencing the network scenario directory. Can be both a real OS path or a memory path.
        hash (str): The hash identifier of the network scenario.
        machines (Dict[str, Kathara.model.Machine]): The devices of the network scenario. Keys are device names, Values
            are Kathara device objects.
        links (Dict[str, Kathara.model.Link]): The collision domains of the network scenario.
            Keys are collision domains names, Values are Kathara collision domain objects.
        general_options (Dict[str, Any]): Keys are option names, values are option values.
        has_dependencies (bool): True if there are dependencies among the devices boot.
        shared_startup_filename (str): The name of the shared startup file, if exists.
        shared_shutdown_filename (str): The name of the shared shutdown file, if exists.
        shared_fs (FS): An object to the path of the network scenario, if the network scenario has a real OS path.
    """
    __slots__ = ['_name', 'description', 'version', 'author', 'email', 'web',
                 'fs', 'hash', 'machines', 'links', 'general_options', 'has_dependencies',
                 'shared_startup_filename', 'shared_shutdown_filename', 'shared_fs']

    def __init__(self, name: Optional[str], path: Optional[str] = None) -> None:
        """Create a new instance of a Kathara network scenario.

        Args:
            name (str): The name of the network scenario.
            path (str): The path to the network scenario directory, if exists.

        Returns:
            None
        """
        self._name: Optional[str] = name
        self.description: Optional[str] = None
        self.version: Optional[str] = None
        self.author: Optional[str] = None
        self.email: Optional[str] = None
        self.web: Optional[str] = None

        self.machines: Dict[str, 'MachinePackage.Machine'] = {}
        self.links: Dict[str, Link] = {}

        self.general_options: Dict[str, Any] = {}

        self.has_dependencies: bool = False

        self.shared_startup_filename: Optional[str] = None
        self.shared_shutdown_filename: Optional[str] = None
        self.shared_fs: Optional[FS] = None

        self.hash: str = utils.generate_urlsafe_hash(path if self._name is None else self._name)

        if path:
            self.fs: FS = fs.open_fs(f"osfs://{path}")

            self.shared_startup_filename = 'shared.startup' if self.fs.exists('shared.startup') else None
            self.shared_shutdown_filename = 'shared.shutdown' if self.fs.exists('shared.shutdown') else None
        else:
            self.fs: FS = fs.open_fs("mem://")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.hash = utils.generate_urlsafe_hash(value)

    def connect_machine_to_link(self, machine_name: str, link_name: str, machine_iface_number: int = None) \
            -> Tuple['MachinePackage.Machine', Link]:
        """Connect the specified device to the specified collision domain.

        Args:
            machine_name (str): The device name.
            link_name (str): The collision domain name.
            machine_iface_number (int): The number of the device interface to connect. If it is None, the first free
                number is used.

        Returns:
            Tuple[Kathara.model.Machine, Kathara.model.Link]: A tuple containing the Kathara device and collision domain
                specified by their names.

        Raises:
            Exception: If an already used interface number is specified.
        """
        machine = self.get_or_new_machine(machine_name)
        link = self.get_or_new_link(link_name)

        machine.add_interface(link, number=machine_iface_number)

        return machine, link

    def assign_meta_to_machine(self, machine_name: str, meta_name: str, meta_value: str) -> 'MachinePackage.Machine':
        """Assign meta information to the specified device.

        Args:
            machine_name (str): The name of the device.
            meta_name (str): The name of the meta property.
            meta_value (str): The value of the meta property.

        Returns:
            Kathara.model.Machine: The Kathara device specified by the name.

        Raises:
            MachineOptionError: If invalid values are specified for meta properties.
        """
        machine = self.get_or_new_machine(machine_name)

        machine.add_meta(meta_name, meta_value)

        return machine

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
                raise LinkNotFoundError("Collision domain `%s` (declared in lab.ext) not found in lab "
                                        "collision domains." % link_name)

            self.links[link_name].external += link_external_links

    def check_integrity(self) -> None:
        """Check if the network interfaces numbers of all the devices in the network scenario are correctly assigned.

        Returns:
            None
        """
        for machine in self.machines:
            self.machines[machine].check()

    def get_links_from_machines(self, selected_machines: Union[List[str], Set[str]]) -> Set[str]:
        """Return the name of the collision domains connected to the selected devices.

        Args:
            selected_machines (Set[str]): A set with selected devices names.

        Returns:
            Set[str]: A set of names of collision domains to deploy.
        """
        # Intersect selected machines names with self.machines keys
        selected_machines = set(self.machines.keys()) & set(selected_machines)
        # Apply filtering
        machines = [v for (k, v) in self.machines.items() if k in selected_machines]

        # Get only selected machines Link objects.
        selected_links = set(chain.from_iterable([machine.interfaces.values() for machine in machines]))
        selected_links = {link.name for link in selected_links}

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

    def new_machine(self, name: str, **kwargs: Dict[str, Any]) -> 'MachinePackage.Machine':
        """Create and add the device to the devices list.

        Args:
            name (str): The name of the device
            **kwargs (Dict[str, Any]): Contains device meta information.
                Keys are meta property names, values are meta property values.

        Returns:
            Kathara.model.Machine: A Kathara device.

        Raises:
            MachineAlreadyExistsError: If the device is already in the network scenario.
        """
        if name in self.machines:
            raise MachineAlreadyExistsError(f"Device {name} already in the network scenario.")

        self.machines[name] = MachinePackage.Machine(self, name, **kwargs)

        return self.machines[name]

    def get_or_new_machine(self, name: str, **kwargs: Dict[str, Any]) -> 'MachinePackage.Machine':
        """Get the specified device. If it not exists, create and add it to the devices list.

        Args:
            name (str): The name of the device
            **kwargs (Dict[str, Any]): Contains device meta information.
                Keys are meta property names, values are meta property values.

        Returns:
            Kathara.model.Machine: A Kathara device.
        """
        if name not in self.machines:
            self.machines[name] = MachinePackage.Machine(self, name, **kwargs)

        return self.machines[name]

    def get_link(self, name: str) -> Link:
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

    def new_link(self, name: str) -> Link:
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

        self.links[name] = Link(self, name)

        return self.links[name]

    def get_or_new_link(self, name: str) -> Link:
        """Get the specified collision domain. If it not exists, create and add it to the collision domains list.

        Args:
            name (str): The name of the collision domain.

        Returns:
            Kathara.model.Link: A Kathara collision domain.
        """
        if name not in self.links:
            self.links[name] = Link(self, name)

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
            self.shared_fs = self.fs.makedir('shared', recreate=True)
            if self.fs.islink('shared'):
                raise ValueError("`shared` folder is a symlink, delete it.")
        except OSError:
            # Do not create shared folder if not permitted.
            return

    def has_host_path(self) -> bool:
        """Check if the network scenario has a directory on the host.

        Returns:
            bool: True if self.fs is a path on the host filesystem, else False.
        """
        return self.fs.__class__ is OSFS

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

    def find_machine(self, machine_name: str) -> bool:
        """Check if the specified device is in the network scenario.

        Args:
            machine_name (str): The name of the device to search.

        Returns:
            bool: True if the device is in the network scenario, else False.
        """
        return machine_name in self.machines.keys()

    def find_machines(self, machine_names: Set[str]) -> bool:
        """Check if the specified devices are in the network scenario.

        Args:
            machine_names (Set[str]): A set of strings containing the names of the devices to search.

        Returns:
            bool: True if the devices are all in the network scenario, else False.
        """
        return all(map(lambda x: self.find_machine(x), machine_names))

    def __repr__(self) -> str:
        return "Lab(%s, %s, %s, %s)" % (self.fs, self.hash, self.machines, self.links)

    def __str__(self) -> str:
        lab_info = ""

        if self._name:
            lab_info += "Name: %s\n" % self._name

        if self.description:
            lab_info += "Description: %s\n" % self.description

        if self.version:
            lab_info += "Version: %s\n" % self.version

        if self.author:
            lab_info += "Author(s): %s\n" % self.author

        if self.email:
            lab_info += "Email: %s\n" % self.email

        if self.web:
            lab_info += "Website: %s\n" % self.web

        return lab_info[0:-1]  # Remove trailing new line
