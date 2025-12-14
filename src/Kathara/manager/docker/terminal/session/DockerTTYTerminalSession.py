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
        return self._external_fd

    def read(self, n: int = 4096) -> bytes:
        if self._closed:
            return b""

        try:
            return os.read(self._external_fd, n)
        except OSError:
            return b""

    def write(self, data: bytes) -> None:
        if self._closed:
            return

        os.write(self._external_fd, data)

    def resize(self, cols: int, rows: int) -> None:
        self._client.api.exec_resize(self._exec_id, height=rows, width=cols)

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        try:
            os.close(self._external_fd)
        except OSError:
            pass
