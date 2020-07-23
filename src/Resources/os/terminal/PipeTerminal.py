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

    # @staticmethod
    # def _handle_resize_terminal_win():
    #     res = None
    #     try:
    #         from ctypes import windll, create_string_buffer
    #
    #         # stdin handle is -10
    #         # stdout handle is -11
    #         # stderr handle is -12
    #
    #         h = windll.kernel32.GetStdHandle(-12)
    #         csbi = create_string_buffer(22)
    #         res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    #     except:
    #         return None
    #
    #     if res:
    #         import struct
    #         (_, _, _, _, _, left, top, right, bottom, _, _) = \
    #             struct.unpack("hhhhHhhhhhh", csbi.raw)
    #         w = right - left + 1
    #         h = bottom - top + 1
    #         return w, h
    #     else:
    #         return None