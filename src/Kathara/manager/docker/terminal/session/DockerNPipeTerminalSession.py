from typing import Any, Optional

import pywintypes
import win32file
import win32pipe
from docker import DockerClient

from .....foundation.manager.terminal.core.ITerminalSession import ITerminalSession


class DockerNPipeSession(ITerminalSession):
    __slots__ = ['_exec_id', '_pipe_handle']

    def __init__(self, handler: Any, client: DockerClient, exec_id: str) -> None:
        super().__init__(handler, client)

        self._exec_id: str = exec_id

        self._pipe_handle: Optional[int] = handler._handle.handle
        win32pipe.SetNamedPipeHandleState(self._pipe_handle, 0x00000001, None, None)

    def read(self, n: int = 4096) -> bytes:
        """Read up to n bytes from the session output stream.

        Args:
            n (int): Maximum number of bytes to read.

        Returns:
            bytes: Data read from the session.
        """
        if self._closed or self._pipe_handle is None:
            return b""

        try:
            _, data = win32file.ReadFile(self._pipe_handle, n, None)
            return data
        except pywintypes.error as e:
            if getattr(e, "winerror", None) in (232, 233):
                return b""
            raise e

    def write(self, data: bytes) -> None:
        """Write bytes to the session input stream.

        Args:
            data (bytes): Data to send to the session.

        Returns:
            None
        """
        if self._closed or self._pipe_handle is None:
            return

        win32file.WriteFile(self._pipe_handle, data)

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

        if self._pipe_handle is not None:
            try:
                win32file.CloseHandle(self._pipe_handle)
            except pywintypes.error:
                pass
            self._pipe_handle = None
