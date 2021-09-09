import os
from typing import Any, Optional, Callable

import msvcrt
import pyuv
import win32pipe
from docker import DockerClient
from docker.errors import APIError

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_windows


class DockerNPipeTerminal(Terminal):
    __slots__ = ['client', 'exec_id', '_check_opened_timer']

    def __init__(self, handler: Any, client: DockerClient, exec_id: str):
        super().__init__(handler)

        self.client: DockerClient = client
        self.exec_id: str = exec_id

        self._check_opened_timer: Optional[pyuv.Timer] = None

    def _start_external(self) -> None:
        terminal_fd = self._convert_pipe_to_fd()

        self._external_terminal = pyuv.Pipe(self._loop)
        self._external_terminal.open(terminal_fd)
        self._external_terminal.set_blocking(False)
        self._external_terminal.start_read(self._read_external_terminal())

        self._check_opened_timer = pyuv.Timer(self._loop)
        self._check_opened_timer.start(self._is_terminal_opened(), 0, 5)

    def _convert_pipe_to_fd(self) -> Any:
        handle_id = self.handler._handle.handle
        win32pipe.SetNamedPipeHandleState(handle_id, 0x00000001, None, None)
        handle_fd = msvcrt.open_osfhandle(handle_id, os.O_APPEND)

        return handle_fd

    def _on_close(self) -> None:
        self._check_opened_timer.close()

    def _write_on_external_terminal(self) -> Callable:
        def write_on_external_terminal(handle, data, error):
            self._external_terminal.stop_read()
            self._external_terminal.write(data)
            self._external_terminal.start_read(self._read_external_terminal())

        return write_on_external_terminal

    def _resize_terminal(self) -> None:
        w, h = get_terminal_size_windows()
        self.client.api.exec_resize(self.exec_id, height=h, width=w)

    def _is_terminal_opened(self) -> Callable:
        def is_terminal_opened(timer_handle):
            try:
                self.client.api.exec_inspect(self.exec_id)
            except APIError:
                self.close()

        return is_terminal_opened
