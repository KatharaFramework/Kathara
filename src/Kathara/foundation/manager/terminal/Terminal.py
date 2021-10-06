import sys
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable

import pyuv


class Terminal(ABC):
    __slots__ = ['handler', '_loop', '_system_stdin', '_system_stdout', '_external_terminal', '_resize_signal']

    def __init__(self, handler: Any) -> None:
        self.handler: Any = handler

        self._loop: Optional[pyuv.Loop] = None
        self._system_stdin: Optional[pyuv.TTY] = None
        self._system_stdout: Optional[pyuv.TTY] = None
        self._external_terminal: Optional[pyuv.TTY] = None
        self._resize_signal: Optional[pyuv.Signal] = None

    def start(self) -> None:
        self._loop = pyuv.Loop.default_loop()

        self._system_stdin = pyuv.TTY(self._loop, sys.stdin.fileno(), True)
        self._system_stdin.set_mode(1)
        self._system_stdin.start_read(self._write_on_external_terminal())

        self._system_stdout = pyuv.TTY(self._loop, sys.stdout.fileno(), False)

        self._start_external()

        self._resize_terminal()

        self._loop.run()

        pyuv.TTY.reset_mode()

    @abstractmethod
    def _start_external(self) -> None:
        pass

    def close(self) -> None:
        self._on_close()

        self._system_stdin.close()
        self._system_stdout.close()
        self._external_terminal.close()

        self._loop.stop()

    @abstractmethod
    def _on_close(self) -> None:
        pass

    def _write_on_external_terminal(self) -> Callable:
        def write_on_external_terminal(handle, data, error):
            self._external_terminal.write(data)

        return write_on_external_terminal

    def _read_external_terminal(self) -> Callable:
        def read_external_terminal(handle, data, error):
            if data:
                self._system_stdout.write(data)

                if data == b"\r\nexit\r\n":
                    self.close()
            else:
                self.close()

        return read_external_terminal

    @abstractmethod
    def _resize_terminal(self) -> None:
        pass
