import os
from typing import Any, Optional

from docker import DockerClient

from .....foundation.manager.terminal.core.ITerminalSession import ITerminalSession


class DockerTTYTerminalSession(ITerminalSession):
    __slots__ = ['_exec_id', '_external_fd']

    def __init__(self, handler: Any, client: DockerClient, exec_id: str) -> None:
        super().__init__(handler, client)

        self._exec_id: str = exec_id
        self._external_fd: int = handler.fileno()

    def fileno(self) -> Optional[int]:
        """Return an OS-level file descriptor for the session, if available.

        Returns:
            Optional[int]: The file descriptor, or None if the session cannot be polled via fd-based readiness APIs.
        """
        return self._external_fd

    def read(self, n: int = 4096) -> bytes:
        """Read up to n bytes from the session output stream.

        Args:
            n (int): Maximum number of bytes to read.

        Returns:
            bytes: Data read from the session.
        """
        if self._closed:
            return b""

        try:
            return os.read(self._external_fd, n)
        except OSError:
            return b""

    def write(self, data: bytes) -> None:
        """Write bytes to the session input stream.

        Args:
            data (bytes): Data to send to the session.

        Returns:
            None
        """
        if self._closed:
            return

        os.write(self._external_fd, data)

    def resize(self, cols: int, rows: int) -> None:
        """Resize the session terminal dimensions.

        Args:
            cols (int): Terminal width in columns.
            rows (int): Terminal height in rows.

        Returns:
            None
        """
        if self._closed:
            return

        self._client.api.exec_resize(self._exec_id, height=rows, width=cols)

    def close(self) -> None:
        """Close the session and release resources.

        Returns:
            None
        """
        if self._closed:
            return

        self._closed = True

        try:
            os.close(self._external_fd)
        except OSError:
            pass
