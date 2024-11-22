from typing import List, BinaryIO, TextIO

from fs.base import FS

from .FilesystemMixin import FilesystemMixin
from ...model.Machine import Machine


class LabFilesystemMixin(FilesystemMixin):
    """Abstraction to manage filesystems of network scenarios.

    Attributes:
        fs (FS): An object referencing a filesystem. Can be both real OS or a memory fs.
    """

    def __init__(self):
        super().__init__()

    def create_startup_file_from_string(self, machine: Machine, commands_string: str):
        """Create the startup file for the specified device from a string.

        Args:
            machine (Machine): The device to create the startup file for.
            commands_string (str): The startup commands for the device.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
        """
        self.create_file_from_string(commands_string, f"{machine.name}.startup")

    def create_startup_file_from_list(self, machine: Machine, commands: List[str]):
        """Create the startup file for the specified device from a list of strings.

        Args:
            machine (Machine): The device to create the startup file for.
            commands (str): The startup commands for the device.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
        """
        self.create_file_from_list(commands, f"{machine.name}.startup")

    def create_startup_file_from_path(self, machine: Machine, src_path: str):
        """Create the startup file for the specified device from an existing file on the host filesystem.

        Args:
            machine (Machine): The device to create the startup file for.
            src_path (str): The path of the file on the host filesystem to copy.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
        """
        self.create_file_from_path(src_path, f"{machine.name}.startup")

    def create_startup_file_from_stream(self, machine: Machine, stream: BinaryIO | TextIO):
        """Create the startup file for a device from a stream.

        Args:
            machine (Machine): The device to create the startup file for.
            stream (Union[BinaryIO, TextIO]): The stream representing the content of the file to create.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            UnsupportedOperation: If the stream is opened without read permissions.
        """
        self.create_file_from_stream(stream, f"{machine.name}.startup")

    def update_startup_file_from_string(self, machine: Machine, commands_string: str):
        """Append the command_string to the startup file for the specified device.

        Args:
            machine (Machine): The device to update the startup file for.
            commands_string (str): The startup commands to add to the device.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
        """
        self.update_file_from_string(commands_string, f"{machine.name}.startup")

    def update_startup_file_from_list(self, machine: Machine, commands: List[str]):
        """Append the commands to the startup file for the specified device.

        Args:
            machine (Machine): The device to update the startup file for.
            commands (str): The startup commands to append to the device.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
        """
        self.update_file_from_list(commands, f"{machine.name}.startup")
