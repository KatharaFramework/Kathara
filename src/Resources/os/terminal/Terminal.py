import sys
import signal
from abc import ABC, abstractmethod

import pyuv


class Terminal(ABC):
    __slots__ = ['handler', '_loop', '_system_stdin', '_system_stdout', '_external_tty', '_resize_signal']

    def __init__(self, handler):
        self.handler = handler

        self._loop = None
        self._system_stdin = None
        self._system_stdout = None
        self._external_tty = None
        self._resize_signal = None

    def start(self):
        self._loop = pyuv.Loop.default_loop()

        self._system_stdin = pyuv.TTY(self._loop, sys.stdin.fileno(), True)
        self._system_stdin.set_mode(1)
        self._system_stdin.start_read(self._write_on_external_tty())

        self._system_stdout = pyuv.TTY(self._loop, sys.stdout.fileno(), False)

        self._start_external()

        # w, h = self._resize_terminal_win()
        self._resize_signal = pyuv.Signal(self._loop)
        self._resize_signal.start(self._resize_terminal_tty, signal.SIGWINCH)

        self._loop.run()

        pyuv.TTY.reset_mode()

    @abstractmethod
    def _start_external(self):
        pass

    def close(self):
        self._on_close()

        self._system_stdin.close()
        self._system_stdout.close()
        self._external_tty.close()

        self._loop.stop()

    @abstractmethod
    def _on_close(self):
        pass

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self._external_tty.write(data)

        return write_on_external_tty

    def _handle_external_tty(self):
        def handle_external_tty(handle, data, error):
            if data:
                self._system_stdout.write(data)

                if data.decode('utf-8').strip() == 'exit':
                    self.close()
            else:
                self.close()

        return handle_external_tty

    @staticmethod
    def _resize_terminal_win():
        res = None
        try:
            from ctypes import windll, create_string_buffer

            # stdin handle is -10
            # stdout handle is -11
            # stderr handle is -12

            h = windll.kernel32.GetStdHandle(-12)
            csbi = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        except:
            return None

        if res:
            import struct
            (_, _, _, _, _, left, top, right, bottom, _, _) = \
                struct.unpack("hhhhHhhhhhh", csbi.raw)
            w = right - left + 1
            h = bottom - top + 1
            return w, h
        else:
            return None

    def _resize_terminal_tty(self):
        def resize_terminal():
            print("Terminal resized)")

        return resize_terminal
