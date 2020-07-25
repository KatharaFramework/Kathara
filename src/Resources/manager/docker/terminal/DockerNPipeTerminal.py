import msvcrt
import os

import pyuv
import win32pipe

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_windows


class DockerNPipeTerminal(Terminal):
    __slots__ = ['client', 'exec_id']

    def __init__(self, handler, client, exec_id):
        super().__init__(handler)

        self.client = client
        self.exec_id = exec_id

    def _start_external(self):
        terminal_fd = self._convert_pipe_to_fd()

        self._external_terminal = pyuv.Pipe(self._loop)
        self._external_terminal.open(terminal_fd)
        self._external_terminal.set_blocking(False)
        self._external_terminal.start_read(self._handle_external_tty())

    def _convert_pipe_to_fd(self):
        handle_id = self.handler._handle.handle
        win32pipe.SetNamedPipeHandleState(handle_id, 0x00000001, None, None)
        handle_fd = msvcrt.open_osfhandle(handle_id, os.O_APPEND)

        return handle_fd

    def _on_close(self):
        pass

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self._external_terminal.stop_read()
            self._external_terminal.write(data)
            self._external_terminal.start_read(self._handle_external_tty())

        return write_on_external_tty

    def _handle_resize_terminal(self):
        w, h = get_terminal_size_windows()
        self.client.api.exec_resize(self.exec_id, height=h, width=w)
