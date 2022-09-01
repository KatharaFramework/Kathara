import collections
import logging
import os
import re
import shutil
import tarfile
import tempfile
from distutils.util import strtobool
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, OrderedDict

from . import Lab as LabPackage
from . import Link as LinkPackage
from .Link import Link
from .. import utils
from ..exceptions import NonSequentialMachineInterfaceError, MachineOptionError, MachineCollisionDomainConflictError
from ..setting.Setting import Setting


class Machine(object):
    """A Kathara device.

    Contains information about the device and the API object to interact with the Manager.

    Attributes:
        lab (Kathara.model.Lab): The Kathara network Scenario of the device.
        name (str): The name of the device.
        interfaces (collection.OrderedDict[int, Kathara.model.Link]): A list of the collision domains of the device.
        meta (Dict[str, Any]): Keys are meta properties name, values are meta properties values.
        startup_commands (List[str]): A list of commands to execute at the device startup.
        api_object (Any): To interact with the current Kathara Manager.
        capabilities (List[str]): The selected capabilities for the device.
        startup_path (str): The path of the device startup file, if exists.
        shutdown_path (str): The path of the device shutdown file, if exists.
        folder (str): The path of the device folder, if exists.
    """
    __slots__ = ['lab', 'name', 'interfaces', 'meta', 'startup_commands', 'api_object', 'capabilities',
                 'startup_path', 'shutdown_path', 'folder']

    def __init__(self, lab: 'LabPackage.Lab', name: str, **kwargs) -> None:
        """Create a new instance of a Kathara device.

        Args:
            lab (Kathara.model.Lab): The Kathara network scenario of the new device.
            name (str): The name of the device.
            **kwargs (Dict[str, Any]): Specifies the optional parameters of the device.

        Returns:
            None
        """
        name = name.strip()
        matches = re.search(r"^[a-z0-9_]{1,30}$", name)
        if not matches:
            raise Exception("Invalid device name `%s`." % name)

        self.lab: LabPackage.Lab = lab
        self.name: str = name

        self.interfaces: OrderedDict[int, Link] = collections.OrderedDict()

        self.meta: Dict[str, Any] = {
            'sysctls': {},
            'envs': {},
            'bridged': False,
            'ports': {},
            'nested': False
        }

        self.startup_commands: List[str] = []

        self.api_object: Any = None

        self.capabilities: List[str] = ["NET_ADMIN", "NET_RAW", "NET_BROADCAST", "NET_BIND_SERVICE", "SYS_ADMIN"]

        self.startup_path: Optional[str] = None
        self.shutdown_path: Optional[str] = None
        self.folder: Optional[str] = None

        if lab.has_path():
            startup_file = os.path.join(lab.path, '%s.startup' % self.name)
            self.startup_path = startup_file if os.path.exists(startup_file) else None

            shutdown_file = os.path.join(lab.path, '%s.shutdown' % self.name)
            self.shutdown_path = shutdown_file if os.path.exists(shutdown_file) else None

            machine_folder = os.path.join(lab.path, '%s' % self.name)
            self.folder = machine_folder if os.path.isdir(machine_folder) else None

        self.update_meta(kwargs)

    def add_interface(self, link: 'LinkPackage.Link', number: int = None) -> None:
        """Add an interface to the device attached to the specified collision domain.

        Args:
            link (Kathara.model.Link): The Kathara collision domain to attach.
            number (int): The number of the new interface. If it is None, the first free number is selected.

        Returns:
            None

        Raises:
            Exception: The interface number specified is already used on the device.
        """
        if number is None:
            number = len(self.interfaces.keys())

        if number in self.interfaces:
            raise Exception("Interface %d already set on device `%s`." % (number, self.name))

        if self.name in link.machines:
            raise MachineCollisionDomainConflictError(
                "Device `%s` is already connected to collision domain `%s`" % (self.name, link.name)
            )

        self.interfaces[number] = link
        link.machines[self.name] = self

    def add_meta(self, name: str, value: Any) -> None:
        """Add a meta property to the device.

        Args:
            name (str): The name of the property.
            value (Any): The value of the property.

        Returns:
            None

        Raises:
            MachineOptionError: The specified value is not valid for the specified property.
        """
        if name == "exec":
            self.startup_commands.append(value)
            return

        if name == "nested":
            self.meta[name] = bool(strtobool(str(value)))

            if "image" in self.meta and self.meta[name]:
                raise MachineOptionError("Cannot activate nesting when a device image is specified.")

            return

        if name == "image":
            if "nested" in self.meta and self.meta["nested"]:
                raise MachineOptionError("Cannot specify a device image when nesting is activated.")

            self.meta[name] = value

            return

        if name == "bridged":
            self.meta[name] = bool(strtobool(str(value)))
            return

        if name == "sysctl":
            matches = re.search(r"^(?P<key>net\.(\w+\.)+\w+)=(?P<value>\w+)$", value)

            # Check for valid kv-pair
            if matches:
                key = matches.group("key").strip()
                val = matches.group("value").strip()

                # Convert to int if possible
                self.meta['sysctls'][key] = int(val) if val.isdigit() else val
            else:
                raise MachineOptionError(
                    "Invalid sysctl value (`%s`) on `%s`, missing `=` or value not in `net.` namespace."
                    % (value, self.name)
                )
            return

        if name == "env":
            matches = re.search(r"^(?P<key>\w+)=(?P<value>\S+)$", value)

            # Check for valid kv-pair
            if matches:
                key = matches.group("key").strip()
                val = matches.group("value").strip()

                self.meta['envs'][key] = val
            else:
                raise MachineOptionError("Invalid env value (`%s`) on `%s`." % (value, self.name))
            return

        if name == "port":
            if '/' in value:
                (ports, protocol) = value.split('/')
            else:
                (ports, protocol) = value, 'tcp'

            if ':' not in ports:
                host_port, guest_port = 3000, ports
            else:
                (host_port, guest_port) = ports.split(':')

            protocol = protocol.lower()
            if protocol not in ['tcp', 'udp', 'sctp']:
                raise MachineOptionError("Port protocol value not valid on `%s`." % self.name)

            try:
                self.meta['ports'][(int(host_port), protocol)] = int(guest_port)
            except ValueError:
                raise MachineOptionError("Port value not valid on `%s`." % self.name)
            return

        self.meta[name] = value

    def check(self) -> None:
        """Sorts interfaces check if there are missing positions.

        Returns:
            None

        Raises:
            NonSequentialMachineInterfaceError: If there is a missing interface number.
        """
        sorted_interfaces = sorted(self.interfaces.items(), key=lambda kv: kv[0])

        logging.debug("`%s` interfaces are %s." % (self.name, sorted_interfaces))

        for i, (num_iface, _) in enumerate(sorted_interfaces):
            if num_iface != i:
                raise NonSequentialMachineInterfaceError("Interface %d missing on device %s." % (i, self.name))

        self.interfaces = collections.OrderedDict(sorted_interfaces)

    def pack_data(self) -> Optional[bytes]:
        """Pack machine data into a .tar.gz file and returns the tar content as a byte array.

        While packing files, it also applies the win2linux patch in order to remove UTF-8 BOM.

        Returns:
            bytes: the tar content.
        """
        # Make a temp folder and create a tar.gz of the lab directory
        temp_path = tempfile.mkdtemp()

        is_empty = True

        with tarfile.open("%s/hostlab.tar.gz" % temp_path, "w:gz") as tar:
            if self.folder:
                machine_files = filter(lambda x: x.is_file(), Path(self.folder).rglob("*"))

                for file in machine_files:
                    file = str(file)

                    if utils.is_excluded_file(file):
                        continue

                    # Removes the last element of the path
                    # (because it's the machine folder name and it should be included in the tar archive)
                    lab_path, machine_folder = os.path.split(self.folder)
                    (tarinfo, content) = utils.pack_file_for_tar(file,
                                                                 arc_name="hostlab/%s" % os.path.relpath(file, lab_path)
                                                                 )
                    tar.addfile(tarinfo, content)

                is_empty = False

            if self.startup_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.startup_path,
                                                             arc_name="hostlab/%s.startup" % self.name
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

            if self.shutdown_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.shutdown_path,
                                                             arc_name="hostlab/%s.shutdown" % self.name
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

            if self.lab.shared_startup_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.lab.shared_startup_path,
                                                             arc_name="hostlab/shared.startup"
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

            if self.lab.shared_shutdown_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.lab.shared_shutdown_path,
                                                             arc_name="hostlab/shared.shutdown"
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

        # If no machine files are found, return None.
        if is_empty:
            return None

        # Read tar.gz content
        with open("%s/hostlab.tar.gz" % temp_path, "rb") as tar_file:
            tar_data = tar_file.read()

        # Delete temporary tar.gz
        shutil.rmtree(temp_path)

        return tar_data

    def get_image(self) -> str:
        """Get the image of the device, if defined in options or device meta. If not, use default one.

        Returns:
            str: The name of the device image.
        """
        if self.meta['nested']:
            return 'kathara/inception'

        return self.lab.general_options["image"] if "image" in self.lab.general_options else \
            self.meta["image"] if "image" in self.meta else Setting.get_instance().image

    def get_mem(self) -> str:
        """Get memory limit, if defined in options. If not, use the value from device meta. Otherwise, return None.

        Returns:
            str: The memory limit of the device.
        """
        memory = self.lab.general_options["mem"] if "mem" in self.lab.general_options else \
            self.meta["mem"] if "mem" in self.meta else None

        if memory:
            unit = memory[-1].lower()
            if unit not in ["b", "k", "m", "g"]:
                try:
                    return "%sm" % int(memory)
                except ValueError:
                    raise MachineOptionError("Memory value not valid on `%s`." % self.name)

            try:
                return "%s%s" % (int(memory[:-1]), unit)
            except ValueError:
                raise MachineOptionError("Memory value not valid on `%s`." % self.name)

        return memory

    def get_cpu(self, multiplier: int = 1) -> Optional[int]:
        """Get the CPU limit, multiplied by a specific multiplier.

        User should pass a float value ranging from 0 to max user CPUs.
        Try to took it from options, or device meta. Otherwise, return None.

        Args:
            multiplier (int): A numeric multiplier for the CPU limit value.

        Returns:
            Optional[int]: The CPU limit of the device.
        """
        if "cpus" in self.lab.general_options:
            try:
                return int(float(self.lab.general_options["cpus"]) * multiplier)
            except ValueError:
                raise MachineOptionError("CPU value not valid on `%s`." % self.name)
        elif "cpus" in self.meta:
            try:
                return int(float(self.meta["cpus"]) * multiplier)
            except ValueError:
                raise MachineOptionError("CPU value not valid on `%s`." % self.name)

        return None

    def get_ports(self) -> Optional[Dict[Tuple[int, str], int]]:
        """Get the port mapping of the device.

        Returns:
            Dict[(int, str), int]: Keys are pairs (host_port, protocol), values specifies the guest_port.
        """
        if self.meta['ports']:
            return self.meta['ports']

        return None

    def get_num_terms(self) -> int:
        """Get the number of terminal to be opened for the device.

        Returns:
            int: The number of terminal to be opened.
        """
        num_terms = 1

        if "num_terms" in self.lab.general_options:
            num_terms = self.lab.general_options['num_terms']
        elif 'num_terms' in self.meta:
            num_terms = self.meta['num_terms']

        try:
            num_terms = int(num_terms)

            if num_terms < 0:
                raise MachineOptionError("Terminals Number value on `%s` must be a positive value or zero." % self.name)
        except ValueError:
            raise MachineOptionError("Terminals Number value not valid on `%s`." % self.name)

        return num_terms

    def is_ipv6_enabled(self) -> bool:
        """Check if IPv6 is enabled on the device.

        Returns:
            bool: True if it is enabled, else False.
        """
        try:
            return bool(strtobool(self.lab.general_options["ipv6"])) if "ipv6" in self.lab.general_options else \
                bool(strtobool(self.meta["ipv6"])) if "ipv6" in self.meta else Setting.get_instance().enable_ipv6
        except ValueError:
            raise MachineOptionError("IPv6 value not valid on `%s`." % self.name)

    def update_meta(self, args: Dict[str, Any]) -> None:
        """Update the device metas from a dict.

        Args:
            args (Dict[str, Any]): Keys are the meta properties names, values are the updated meta properties values.

        Returns:
            None
        """
        if 'exec_commands' in args and args['exec_commands'] is not None:
            for command in args['exec_commands']:
                self.add_meta("exec", command)

        if 'mem' in args and args['mem'] is not None:
            self.add_meta("mem", args['mem'])

        if 'cpus' in args and args['cpus'] is not None:
            self.add_meta("cpus", args['cpus'])

        if 'image' in args and args['image'] is not None:
            self.add_meta("image", args['image'])

        if 'bridged' in args and args['bridged'] is not None and args['bridged']:
            self.add_meta("bridged", True)

        if 'nested' in args and args['nested'] is not None and args['nested']:
            self.add_meta("nested", True)

        if 'ports' in args and args['ports'] is not None:
            for port in args['ports']:
                self.add_meta("port", port)

        if 'num_terms' in args and args['num_terms'] is not None:
            self.add_meta('num_terms', args['num_terms'])

        if 'sysctls' in args and args['sysctls'] is not None:
            for sysctl in args['sysctls']:
                self.add_meta("sysctl", sysctl)

        if 'envs' in args and args['envs'] is not None:
            for envs in args['envs']:
                self.add_meta("env", envs)

    def __repr__(self) -> str:
        return "Machine(%s, %s, %s)" % (self.name, self.interfaces, self.meta)

    def __str__(self) -> str:
        formatted_machine = f"Name: {self.name}"
        formatted_machine += f"\nImage: {self.get_image()}"

        if self.interfaces:
            formatted_machine += "\nInterfaces: "
            for (iface_num, link) in self.interfaces.items():
                formatted_machine += f"\n\t- {iface_num}: {link.name}"

        formatted_machine += f"\nBridged Connection: {self.meta['bridged']}"

        if self.meta["sysctls"]:
            formatted_machine += "\nSysctls:"
            for (key, value) in self.meta["sysctls"].items():
                formatted_machine += f"\n\t- {key} = {value}"

        if self.meta["ports"]:
            formatted_machine += "\nExposed Ports:"
            for (key, value) in self.meta["ports"].items():
                formatted_machine += f"\n\t- Host: {key} -> Guest: {value}"

        return formatted_machine
