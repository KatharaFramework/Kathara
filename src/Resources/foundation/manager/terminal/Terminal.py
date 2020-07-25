import sys
from abc import ABC, abstractmethod

import pyuv


class Terminal(ABC):
    __slots__ = ['handler', '_loop', '_system_stdin', '_system_stdout', '_external_terminal', '_resize_signal']

    def __init__(self, handler):
        self.handler = handler

        self._loop = None
        self._system_stdin = None
        self._system_stdout = None
        self._external_terminal = None
        self._resize_signal = None

    def start(self):
        self._loop = pyuv.Loop.default_loop()

        self._system_stdin = pyuv.TTY(self._loop, sys.stdin.fileno(), True)
        self._system_stdin.set_mode(1)
        self._system_stdin.start_read(self._write_on_external_tty())

        self._system_stdout = pyuv.TTY(self._loop, sys.stdout.fileno(), False)

        self._start_external()

        self._handle_resize_terminal()

        self._loop.run()

        pyuv.TTY.reset_mode()

    @abstractmethod
    def _start_external(self):
        pass

    def close(self):
        self._on_close()

        self._system_stdin.close()
        self._system_stdout.close()
        self._external_terminal.close()

        self._loop.stop()

    @abstractmethod
    def _on_close(self):
        pass

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self._external_terminal.write(data)

        return write_on_external_tty

    def _handle_external_tty(self):
        def handle_external_tty(handle, data, error):
            self._system_stdout.write(data)

            if data.decode('utf-8').strip() == 'exit':
                self.close()

        return handle_external_tty

    @abstractmethod
    def _handle_resize_terminal(self):
        pass
