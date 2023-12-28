import collections
import logging
import re
from io import BytesIO
from typing import Dict, Any, Tuple, Optional, List, OrderedDict, TextIO, Union, BinaryIO

# noinspection PyUnresolvedReferences
from fs._bulk import Copier
from fs.base import FS
from fs.copy import copy_fs, copy_file
from fs.tarfs import WriteTarFS
# noinspection PyUnresolvedReferences
from fs.tempfs import TempFS
from fs.walk import Walker

from . import Interface as InterfacePackage
from . import Lab as LabPackage
from . import Link as LinkPackage
from .. import utils
from ..exceptions import NonSequentialMachineInterfaceError, MachineOptionError, MachineCollisionDomainError
from ..foundation.model.FilesystemMixin import FilesystemMixin
from ..setting.Setting import Setting
from ..trdparty.strtobool.strtobool import strtobool

MACHINE_CAPABILITIES: List[str] = ["NET_ADMIN", "NET_RAW", "NET_BROADCAST", "NET_BIND_SERVICE", "SYS_ADMIN"]


class Machine(FilesystemMixin):
    """A Kathara device.

    Contains information about the device and the API object to interact with the Manager.

    Attributes:
        lab (Kathara.model.Lab): The Kathara network Scenario of the device.
        name (str): The name of the device.
        interfaces (collection.OrderedDict[int, Kathara.model.Link]): A list of the collision domains of the device.
        meta (Dict[str, Any]): Keys are meta properties name, values are meta properties values.
        api_object (Any): To interact with the current Kathara Manager.
        fs (fs.FS): The filesystem of the device. Contains files and configurations associated to it.
    """
    __slots__ = ['lab', 'name', 'interfaces', 'meta', 'api_object']

    def __init__(self, lab: 'LabPackage.Lab', name: str, **kwargs) -> None:
        """Create a new instance of a Kathara device.

        Args:
            lab (Kathara.model.Lab): The Kathara network scenario of the new device.
            name (str): The name of the device.
            **kwargs (Dict[str, Any]): Specifies the optional parameters of the device.

        Returns:
            None
        """
        super().__init__()

        name = name.strip()
        matches = re.search(r"^[a-z0-9_]{1,30}$", name)
        if not matches:
            raise SyntaxError(f"Invalid device name `{name}`.")

        self.lab: LabPackage.Lab = lab
        self.name: str = name

        self.interfaces: OrderedDict[int, 'InterfacePackage.Interface'] = collections.OrderedDict()

        self.meta: Dict[str, Any] = {
            'exec_commands': [],
            'sysctls': {},
            'envs': {},
            'ports': {},
        }

        self.api_object: Any = None

        self.fs: FS = self.lab.fs.opendir(self.name) \
            if self.lab.fs.exists(self.name) and self.lab.fs.isdir(self.name) else None

        self.update_meta(kwargs)

    def add_interface(self, link: 'LinkPackage.Link', number: int = None, mac_address: str = None) \
            -> 'InterfacePackage.Interface':
        """Add an interface to the device attached to the specified collision domain.

        Args:
            link (Kathara.model.Link): The Kathara collision domain to attach.
            number (int): The number of the new interface. If it is None, the first free number is selected.
            mac_address (str): The MAC address of the interface. If None, a generated MAC address
                is associated when the Machine is started.

        Returns:
            Interface: The object associated to this interface.

        Raises:
            MachineCollisionDomainConflictError: If the interface number specified is already used on the device.
            MachineCollisionDomainConflictError: If the device is already connected to the collision domain.
        """
        if number is None:
            number = len(self.interfaces.keys())

        if number in self.interfaces:
            raise MachineCollisionDomainError(f"Interface {number} already set on device `{self.name}`.")

        if self.name in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{self.name}` is already connected to collision domain `{link.name}`."
            )

        interface = InterfacePackage.Interface(self, link, number, mac_address)
        self.interfaces[number] = interface
        link.machines[self.name] = self

        return interface

    def remove_interface(self, link: 'LinkPackage.Link') -> None:
        """Disconnect the device from the specified collision domain.

        Args:
            link (Kathara.model.Link): The Kathara collision domain to disconnect.

        Returns:
            None

        Raises:
            MachineCollisionDomainConflictError: If the device is not connected to the collision domain.
        """
        if self.name not in link.machines:
            raise MachineCollisionDomainError(
                f"Device `{self.name}` is not connected to collision domain `{link.name}`."
            )

        self.interfaces = collections.OrderedDict(
            map(
                lambda x: x if x[1] is not None and x[1].link.name != link.name else (x[0], None),
                self.interfaces.items()
            )
        )
        link.machines.pop(self.name)

    def add_meta(self, name: str, value: Any) -> None:
        """Add a meta property to the device.

        Args:
            name (str): The name of the property.
            value (Any): The value of the property.

        Returns:
            Optional[Any]: Previous value if meta was already assigned, None otherwise.

        Raises:
            MachineOptionError: If the specified value is not valid for the specified property.
        """
        if name == "exec":
            self.meta['exec_commands'].append(value)
            return None

        if name == "bridged":
            old_value = self.meta[name] if name in self.meta else None
            self.meta[name] = strtobool(str(value))
            return old_value

        if name == "sysctl":
            matches = re.search(r"^(?P<key>net\.([\w-]+\.)+[\w-]+)=(?P<value>-?\w+)$", value)

            # Check for valid kv-pair
            if matches:
                key = matches.group("key").strip()
                val = matches.group("value").strip()

                old_value = self.meta['sysctls'][key] if key in self.meta['sysctls'] else None

                # Convert to int if possible
                self.meta['sysctls'][key] = int(val) if val.strip('-').isnumeric() else val
            else:
                raise MachineOptionError(
                    "Invalid sysctl value (`%s`) on `%s`, missing `=` or value not in `net.` namespace."
                    % (value, self.name)
                )
            return old_value

        if name == "env":
            matches = re.search(r"^(?P<key>\w+)=(?P<value>\S+)$", value)

            # Check for valid kv-pair
            if matches:
                key = matches.group("key").strip()
                val = matches.group("value").strip()

                old_value = self.meta['envs'][key] if key in self.meta['envs'] else None

                self.meta['envs'][key] = val
            else:
                raise MachineOptionError("Invalid env value (`%s`) on `%s`." % (value, self.name))
            return old_value

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
                key_tuple = (int(host_port), protocol)

                old_value = self.meta['ports'][key_tuple] if key_tuple in self.meta['ports'] else None

                self.meta['ports'][key_tuple] = int(guest_port)
            except ValueError:
                raise MachineOptionError("Port value not valid on `%s`." % self.name)
            return old_value

        old_value = self.meta[name] if name in self.meta else None
        self.meta[name] = value
        return old_value

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

        if 'ipv6' in args and args['ipv6'] is not None:
            self.add_meta("ipv6", args['ipv6'])

        if 'shell' in args and args['shell'] is not None:
            self.add_meta("shell", args['shell'])

    def check(self) -> None:
        """Sort interfaces and check if there are missing interface numbers.

        Returns:
            None

        Raises:
            NonSequentialMachineInterfaceError: If there is a missing interface number.
        """
        sorted_interfaces = sorted(self.interfaces.items(), key=lambda kv: kv[0])

        logging.debug("`%s` interfaces are %s." % (self.name, sorted_interfaces))

        for i, (num_iface, _) in enumerate(sorted_interfaces):
            if num_iface != i:
                raise NonSequentialMachineInterfaceError(i, self.name)

        self.interfaces = collections.OrderedDict(sorted_interfaces)

    def pack_data(self) -> Optional[bytes]:
        """Pack machine data into a .tar.gz file and returns the tar content as a byte array.

        While packing files, it also applies the win2linux patch in order to remove UTF-8 BOM.

        Returns:
            bytes: the tar content.
        """
        is_empty = True

        file = BytesIO()
        with WriteTarFS(file, compression="gz") as tar:
            hostlab_tar_dir = tar.makedir('hostlab')
            machine_tar_dir = hostlab_tar_dir.makedir(self.name)
            if self.fs and not self.fs.isempty(''):
                copy_fs(
                    self.fs,
                    machine_tar_dir,
                    on_copy=lambda src_fs, src_path, dst_fs, dst_path: utils.convert_win_2_linux(
                        dst_fs.getsyspath(dst_path), write=True
                    ),
                    walker=Walker(exclude=utils.EXCLUDED_FILES)
                )

                is_empty = False

            for name in [f"{self.name}.startup", f"{self.name}.shutdown", "shared.startup", "shared.shutdown"]:
                if self.lab.fs.exists(name):
                    copy_file(self.lab.fs, name, hostlab_tar_dir, name)
                    utils.convert_win_2_linux(hostlab_tar_dir.getsyspath(name), write=True)
                    is_empty = False

        if not is_empty:
            file.seek(0)
            return file.read()

        # If no machine files are found, return None.
        return None

    def get_exec_commands(self) -> List[str]:
        """Get the device exec commands.

        Returns:
            List[str]: The list containing the additional commands.
        """
        return self.meta['exec_commands']

    def is_bridged(self) -> bool:
        """Return True if the device is bridged, else return False.

        Returns:
            bool: True if the device is bridged, else False.
        """
        if "bridged" not in self.meta:
            return False

        return self.meta['bridged']

    def get_sysctls(self) -> Dict[str, Union[int, str]]:
        """Get the sysctls specified for the device.

        Returns:
            Dict[str, Union[int, str]]: Keys contain the sysctls to set, values are the values to apply.
        """
        return self.meta['sysctls']

    def get_envs(self) -> Dict[str, Union[int, str]]:
        """Get the environment variables specified for the device.

        Returns:
            Dict[str, Union[int, str]]: Keys are environment variables to set, values are the values to apply.
        """
        return self.meta['envs'] if self.meta['envs'] else {}

    def get_ports(self) -> Dict[Tuple[int, str], int]:
        """Get the port mapping of the device.

        Returns:
            Dict[(int, str), int]: Keys are pairs (host port, protocol), values specifies the guest port.
        """
        return self.meta['ports']

    def get_image(self) -> str:
        """Get the image of the device, if defined in options or device meta. If not, use default one.

        Returns:
            str: The name of the device image.
        """
        return self.lab.general_options["image"] if "image" in self.lab.general_options else \
            self.meta["image"] if "image" in self.meta else Setting.get_instance().image

    def get_mem(self) -> str:
        """Get memory limit, if defined in options. If not, use the value from device meta. Otherwise, return None.

        Returns:
            str: The memory limit of the device.

        Raises:
            MachineOptionError: If the memory value specified is not valid.
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
        Try to take it from options, or device meta. Otherwise, return None.

        Args:
            multiplier (int): A numeric multiplier for the CPU limit value.

        Returns:
            Optional[int]: The CPU limit of the device.

        Raises:
            MachineOptionError: If the CPU value specified is not valid.
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

    def get_shell(self) -> str:
        """Get the custom shell specified for the device.

        Returns:
            str: The path of the custom shell specified for connecting to the device.
        """
        return self.meta['shell'] if 'shell' in self.meta else Setting.get_instance().device_shell

    def get_num_terms(self) -> int:
        """Get the number of terminals to be opened for the device.

        Returns:
            int: The number of terminals to be opened.

        Raises:
            MachineOptionError: If the terminals number value specified is not valid.
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

        Raises:
            MachineOptionError: If the IPv6 value specified is not valid.
        """
        is_v6_enabled = Setting.get_instance().enable_ipv6

        try:
            if "ipv6" in self.lab.general_options:
                is_v6_enabled = self.lab.general_options["ipv6"]
            elif "ipv6" in self.meta:
                is_v6_enabled = self.meta["ipv6"]

            return is_v6_enabled if type(is_v6_enabled) == bool else strtobool(is_v6_enabled)
        except ValueError:
            raise MachineOptionError("IPv6 value not valid on `%s`." % self.name)

    # Override FilesystemMixin methods to handle the condition if we want to add a file but self.fs is not set
    # In this case, we create the machine directory and assign it to self.fs before calling the actual method
    def create_file_from_string(self, content: str, dst_path: str) -> None:
        """Create a file from a string in the device fs. If fs is None, create it in the network scenario.

        Args:
            content (str): The string representing the content of the file to create.
            dst_path (str): The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            fs.errors.ResourceNotFound: If the path is not found.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().create_file_from_string(content, dst_path)

    def update_file_from_string(self, content: str, dst_path: str) -> None:
        """Update a file in the fs object from a string.

        Args:
            content (str): The string representing the content for updating the file.
            dst_path (str): The absolute path on the fs of the file to update.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().update_file_from_string(content, dst_path)

    def create_file_from_list(self, lines: List[str], dst_path: str) -> None:
        """Create a file from a list of strings in the device fs. If fs is None, create it in the network scenario.

        Args:
            lines (List[str]): The list of strings representing the content of the file to create.
            dst_path (str): The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            fs.errors.ResourceNotFound: If the path is not found.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().create_file_from_list(lines, dst_path)

    def update_file_from_list(self, lines: List[str], dst_path: str) -> None:
        """Update a file in the fs object from a list of strings.

        Args:
            lines (List[str]): The list of strings representing the content for updating the file.
            dst_path (str): The absolute path on the fs of the file to upload.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().update_file_from_list(lines, dst_path)

    def create_file_from_path(self, src_path: str, dst_path: str) -> None:
        """Create a file in the device fs from an existing file on the host filesystem. If the fs is None, create it.

        Args:
            src_path (str): The path of the file on the host filesystem to copy in the fs object.
            dst_path (str): The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            fs.errors.ResourceNotFound: If the path is not found.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().create_file_from_path(src_path, dst_path)

    def create_file_from_stream(self, stream: Union[BinaryIO, TextIO], dst_path: str) -> None:
        """Create a file in the device fs from a stream. If fs is None, create it in the network scenario.

        Args:
            stream (Union[BinaryIO, TextIO]): The stream representing the content of the file to create.
            dst_path (str): The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            UnsupportedOperation: If the stream is opened without read permissions.
            fs.errors.ResourceNotFound: If the path is not found.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().create_file_from_stream(stream, dst_path)

    def copy_directory_from_path(self, src_path: str, dst_path: str) -> None:
        """Copy a directory from a src_path in the host filesystem into a dst_path in the fs of the device.

        Args:
             src_path (str): The source path of the directory to copy.
             dst_path (str): The destination path on the device where to copy the directory.

        Returns:
            None
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        super().copy_directory_from_path(src_path, dst_path)

    def write_line_before(self, file_path: str, line_to_add: str, searched_line: str, first_occurrence: bool = False) \
            -> int:
        """Write a new line before a specific line in a file.

        Args:
            file_path (str): The path of the file to add the new line.
            line_to_add (str): The new line to add before the searched line.
            searched_line (str): The searched line.
            first_occurrence (bool): Inserts line only before the first occurrence. Default is False.

        Returns:
            int: Number of times the line has been added.

        Raises:
            fs.errors.FileExpected: If the path is not a file.
            fs.errors.ResourceNotFound: If the path does not exist.
            LineNotFoundError: If the searched line is not found in the file.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        return super().write_line_before(file_path, line_to_add, searched_line, first_occurrence)

    def write_line_after(self, file_path: str, line_to_add: str, searched_line: str, first_occurrence: bool = False) \
            -> int:
        """Write a new line after a specific line in a file.

        Args:
            file_path (str): The path of the file to add the new line.
            line_to_add (str): The new line to add after the searched line.
            searched_line (str): The searched line.
            first_occurrence (bool): Inserts line only after the first occurrence. Default is False.

        Returns:
            int: Number of times the line has been added.

        Raises:
            fs.errors.FileExpected: If the path is not a file.
            fs.errors.ResourceNotFound: If the path does not exist.
            LineNotFoundError: If the searched line is not found in the file.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        return super().write_line_after(file_path, line_to_add, searched_line, first_occurrence)

    def delete_line(self, file_path: str, line_to_delete: str, first_occurrence: bool = False) -> int:
        """Delete a specified line in a file.

        Args:
            file_path (str): The path of the file to delete the line.
            line_to_delete (str): The line to delete.
            first_occurrence (bool): Deletes only first occurrence. Default is False.

        Returns:
            int: Number of times the line has been deleted.

        Raises:
            fs.errors.FileExpected: If the path is not a file.
            fs.errors.ResourceNotFound: If the path does not exist.
            LineNotFoundError: If the searched line is not found in the file.
        """
        if not self.fs:
            self.fs = self.lab.fs.makedir(self.name, recreate=True)

        return super().delete_line(file_path, line_to_delete, first_occurrence)

    def __repr__(self) -> str:
        return "Machine(%s, %s, %s)" % (self.name, self.interfaces, self.meta)

    def __str__(self) -> str:
        formatted_machine = f"Name: {self.name}"
        formatted_machine += f"\nImage: {self.get_image()}"

        if self.interfaces:
            formatted_machine += "\nInterfaces: "
            for (iface_num, interface) in self.interfaces.items():
                if interface:
                    formatted_machine += f"\n\t- {iface_num}: {interface.link.name}"
                    if interface.mac_address:
                        formatted_machine += f" (MAC Address: {interface.mac_address})"

        if 'bridged' in self.meta:
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
