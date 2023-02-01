import io
import os.path
from typing import Optional, List, BinaryIO, TextIO, Union

from fs.base import FS

from ...exceptions import InvocationError


class FilesystemMixin(object):
    """
    Attributes:
        fs (FS): An object referencing a filesystem. Can be both real OS or a memory fs.
    """

    def __init__(self):
        self.fs: Optional[FS] = None

    def fs_type(self) -> Optional[str]:
        return self.fs.__class__.__name__.lower().replace("fs", "") if self.fs else None

    def fs_path(self) -> Optional[str]:
        return self.fs.getsyspath("") if self.fs.hassyspath("") else self.fs.__repr__() if self.fs else None

    def create_file_from_string(self, content: str, dst_path: str) -> None:
        if not self.fs:
            raise InvocationError("Cannot create a file if the filesystem is not set.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        with self.fs.open(dst_path, "w") as dst_file:
            dst_file.write(content)

    def create_file_from_list(self, lines: List[str], dst_path: str) -> None:
        if not self.fs:
            raise InvocationError("Cannot create a file if the filesystem is not set.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        with self.fs.open(dst_path, "w") as dst_file:
            dst_file.writelines(line + '\n' for line in lines)

    def create_file_from_path(self, src_path: str, dst_path: str) -> None:
        if not self.fs:
            raise InvocationError("Cannot create a file if the filesystem is not set.")

        directory = os.path.dirname(dst_path)
        self.fs.makedirs(directory, recreate=True)

        with open(src_path, "rb") as dst_file:
            self.fs.upload(dst_path, dst_file)

    def create_file_from_stream(self, stream: Union[BinaryIO, TextIO], dst_path: str) -> None:
        if not self.fs:
            raise InvocationError("Cannot create a file if the filesystem is not set.")

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
