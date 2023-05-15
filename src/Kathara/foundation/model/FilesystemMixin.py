import io
import os.path
from typing import Optional, List, BinaryIO, TextIO, Union

from fs.base import FS

from ...exceptions import InvocationError


class FilesystemMixin(object):
    """Abstraction to manage filesystems of devices and network scenarios.

    Attributes:
        fs (FS): An object referencing a filesystem. Can be both real OS or a memory fs.
    """

    __slots__ = ['fs']

    def __init__(self):
        self.fs: Optional[FS] = None

    def fs_type(self) -> Optional[str]:
        """Return the name of the class of the fs object, if present. Else, return None.

        Returns:
            Optional[str]: The name of the class of the fs object.
        """
        return self.fs.__class__.__name__.lower().replace("fs", "") if self.fs else None

    def fs_path(self) -> Optional[str]:
        """Return the path of the filesystem, if fs has a path on the host. Else, return None

        Returns:
            Optional[str]: The path of the filesystem in the fs.
        """
        return (self.fs.getsyspath("") if self.fs.hassyspath("") else None) if self.fs else None

    def create_file_from_string(self, content: str, dst_path: str) -> None:
        """Create a file in the fs object from a string.

        Args:
            content[str]: The string representing the content of the file to create.
            dst_path[str]: The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            raise InvocationError("Cannot create a file if the filesystem is not set.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        with self.fs.open(dst_path, "w") as dst_file:
            dst_file.write(content)

    def update_file_from_string(self, content: str, dst_path: str) -> None:
        """Update a file in the fs object from a string.

        Args:
            content[str]: The string representing the content for updating the file.
            dst_path[str]: The absolute path on the fs of the file to update.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            raise InvocationError("There is no filesystem associated to this network scenario.")

        with self.fs.open(dst_path, "a") as dst_file:
            dst_file.write(content)

    def create_file_from_list(self, lines: List[str], dst_path: str) -> None:
        """Create a file in the fs object from a list of strings.

        Args:
            content[str]: The list of strings representing the content of the file to create.
            dst_path[str]: The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            raise InvocationError("There is no filesystem associated to this network scenario.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        with self.fs.open(dst_path, "w") as dst_file:
            dst_file.writelines(line + '\n' for line in lines)

    def update_file_from_list(self, lines: List[str], dst_path: str) -> None:
        """Update a file in the fs object from a list of strings.

        Args:
            content[str]: The list of strings representing the content for updating the file.
            dst_path[str]: The absolute path on the fs of the file to upload.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            raise InvocationError("There is no filesystem associated to this network scenario.")

        with self.fs.open(dst_path, "a") as dst_file:
            dst_file.writelines(line + '\n' for line in lines)

    def create_file_from_path(self, src_path: str, dst_path: str) -> None:
        """Create a file in the fs object from an existing file on the host filesystem.

        Args:
            src_path[str]: The path of the file on the host filesystem to copy in the fs object.
            dst_path[str]: The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            raise InvocationError("There is no filesystem associated to this network scenario.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        with open(src_path, "rb") as dst_file:
            self.fs.upload(dst_path, dst_file)

    def create_file_from_stream(self, stream: Union[BinaryIO, TextIO], dst_path: str) -> None:
        """Create a file in the fs object from a stream.

        Args:
            stream[Union[BinaryIO, TextIO]]: The stream representing the content of the file to create.
            dst_path[str]: The absolute path of the fs where create the file.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            UnsupportedOperation: If the stream is opened without read permissions.
            fs.errors.ResourceNotFound: If the path is not found in the fs.
        """
        if not self.fs:
            raise InvocationError("There is no filesystem associated to this network scenario.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        try:
            if "b" in stream.mode:
                self.fs.upload(dst_path, stream)
            else:
                with self.fs.open(dst_path, "w") as dst_file:
                    dst_file.writelines(stream.readlines())
        except io.UnsupportedOperation:
            raise io.UnsupportedOperation("To create a file from stream, you must open it with read permissions.")

    def remove_file(self, file_path: str) -> None:
        """Delete the specified file in the fs object.

        Args:
            file_path[str]: The absolute path on the fs of the file to delete.

        Returns:
            None

        Raises:
            InvocationError: If the fs is None.
            fs.errors.FileExpected: If the path is a directory.
            fs.errors.ResourceNotFound: If the path does not exist.
        """
        if not self.fs:
            raise InvocationError("There is no filesystem associated to this network scenario.")

        self.fs.remove(file_path)
