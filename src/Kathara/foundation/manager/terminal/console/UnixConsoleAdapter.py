import fcntl
import os
import signal
import struct
import sys
import termios
import tty
from typing import Any, Optional, Callable, Tuple

from ..core.IConsoleAdapter import IConsoleAdapter


def get_terminal_size_unix() -> Tuple[int, int]:
    buf = struct.pack("HHHH", 0, 0, 0, 0)
    res = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, buf)
    rows, cols, _, _ = struct.unpack("HHHH", res)
    return cols, rows


class UnixConsoleAdapter(IConsoleAdapter):
    __slots__ = ["_stdin_fd", "_stdout_fd", "_orig_term_attrs", "_resize_handler_installed", "_stdin_reader_installed"]

    def __init__(self) -> None:
        self._stdin_fd: int = sys.stdin.fileno()
        self._stdout_fd: int = sys.stdout.fileno()

        self._orig_term_attrs: Optional[list] = None

        self._resize_handler_installed: bool = False
        self._stdin_reader_installed: bool = False

    def enter_raw(self) -> None:
        self._orig_term_attrs = termios.tcgetattr(self._stdin_fd)
        tty.setraw(self._stdin_fd)

    def exit_raw(self) -> None:
        if self._orig_term_attrs is not None:
            termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._orig_term_attrs)
            self._orig_term_attrs = None

    def install_input_reader(self, loop: Any, on_bytes: Callable[[bytes], None], on_close: Callable[[], None]) -> None:
        if self._stdin_reader_installed:
            return

        def _on_readable() -> None:
            try:
                data = os.read(self._stdin_fd, 4096)
            except OSError:
                on_close()
                return

            if not data:
                on_close()
                return

            on_bytes(data)

        loop.add_reader(self._stdin_fd, _on_readable)
        self._stdin_reader_installed = True

    def remove_input_reader(self, loop: Any) -> None:
        if not self._stdin_reader_installed:
            return

        try:
            loop.remove_reader(self._stdin_fd)
        except Exception:
            pass

        self._stdin_reader_installed = False

    def write_stdout(self, data: bytes) -> None:
        os.write(self._stdout_fd, data)

    def watch_resize(self, loop: Any, cb: Callable[[int, int], None]) -> None:
        def _emit_resize() -> None:
            cols, rows = get_terminal_size_unix()
            cb(cols, rows)

        try:
            loop.add_signal_handler(signal.SIGWINCH, _emit_resize)
            self._resize_handler_installed = True
        except Exception:
            signal.signal(signal.SIGWINCH, lambda *_: _emit_resize())
            self._resize_handler_installed = True

        _emit_resize()

    def unwatch_resize(self, loop: Any) -> None:
        if not self._resize_handler_installed:
            return

        try:
            loop.remove_signal_handler(signal.SIGWINCH)
        except Exception:
            pass

        self._resize_handler_installed = False
