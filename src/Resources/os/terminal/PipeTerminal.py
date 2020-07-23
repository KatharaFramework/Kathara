import msvcrt
import os

import pyuv
import win32pipe

from .Terminal import Terminal


class PipeTerminal(Terminal):
    def _start_external(self):
        terminal_fd = self._convert_pipe_to_fd()

        self._external_tty = pyuv.Pipe(self._loop)
        self._external_tty.open(terminal_fd)
        self._external_tty.set_blocking(False)
        self._external_tty.start_read(self._handle_external_tty())

    def _convert_pipe_to_fd(self):
        handle_id = self.handler._handle.handle
        win32pipe.SetNamedPipeHandleState(handle_id, 0x00000001, None, None)
        handle_fd = msvcrt.open_osfhandle(handle_id, os.O_APPEND)

        return handle_fd

    def _on_close(self):
        pass

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self._external_tty.stop_read()
            self._external_tty.write(data)
            self._external_tty.start_read(self._handle_external_tty())

        return write_on_external_tty
