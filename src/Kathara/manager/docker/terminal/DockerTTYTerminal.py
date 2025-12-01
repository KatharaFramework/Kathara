import os
import signal
import sys
import termios
import tty
from typing import Any, Optional, List

from docker import DockerClient

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_unix


class DockerTTYTerminal(Terminal):
    __slots__ = ["client", "exec_id", "_orig_term_attrs", "_external_fd"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str):
        super().__init__(handler)

        self.client: DockerClient = client
        self.exec_id: str = exec_id

        self._orig_term_attrs: Optional[List] = None
        self._external_fd: Optional[int] = None

    def _start_external(self) -> None:
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        self._external_fd = self.handler.fileno()

        self._orig_term_attrs = termios.tcgetattr(stdin_fd)
        tty.setraw(stdin_fd)

        self._loop.add_reader(stdin_fd, self._on_stdin_readable, stdin_fd)
        self._loop.add_reader(self._external_fd, self._on_external_readable, stdout_fd)

    def _on_stdin_readable(self, stdin_fd: int) -> None:
        try:
            data = os.read(stdin_fd, 4096)
        except OSError:
            self.close()
            return

        if not data:
            self.close()
            return

        if self._external_fd is None:
            self.close()
            return

        try:
            os.write(self._external_fd, data)
        except OSError:
            self.close()

    def _on_external_readable(self, stdout_fd: int) -> None:
        if self._external_fd is None:
            self.close()
            return

        try:
            data = os.read(self._external_fd, 4096)
        except OSError:
            self.close()
            return

        if not data:
            self.close()
            return

        try:
            os.write(stdout_fd, data)
        except OSError:
            self.close()
            return

        if data == b"\r\nexit\r\n":
            self.close()

    def _on_close(self) -> None:
        stdin_fd = sys.stdin.fileno()

        try:
            self._loop.remove_reader(stdin_fd)
        except Exception:
            pass

        if self._external_fd is not None:
            try:
                self._loop.remove_reader(self._external_fd)
            except Exception:
                pass
            try:
                os.close(self._external_fd)
            except OSError:
                pass
            self._external_fd = None

        try:
            self._loop.remove_signal_handler(signal.SIGWINCH)
        except Exception:
            pass

        if self._orig_term_attrs is not None:
            termios.tcsetattr(
                sys.stdin.fileno(),
                termios.TCSADRAIN,
                self._orig_term_attrs,
            )

    def _resize_terminal(self) -> None:
        def resize() -> None:
            cols, rows = get_terminal_size_unix()
            self.client.api.exec_resize(
                self.exec_id,
                height=rows,
                width=cols,
            )

        try:
            self._loop.add_signal_handler(signal.SIGWINCH, resize)
        except Exception:
            signal.signal(signal.SIGWINCH, lambda a, b: resize())

        resize()
