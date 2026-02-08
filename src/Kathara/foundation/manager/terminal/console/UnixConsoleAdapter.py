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
    """Get the current terminal size (Unix).

    Returns:
        Tuple[int, int]: a tuple containing (cols, rows).
    """
    buf = struct.pack("HHHH", 0, 0, 0, 0)
    res = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, buf)
    rows, cols, _, _ = struct.unpack("HHHH", res)
    return cols, rows


class UnixConsoleAdapter(IConsoleAdapter):
    """Unix-specific console adapter.

    Attributes:
        _stdin_fd (int): File descriptor for stdin.
        _stdout_fd (int): File descriptor for stdout.
        _orig_term_attrs (Optional[list]): Saved terminal attributes for restoring on exit_raw().
        _resize_handler_installed (bool): Whether resize watching is active.
        _stdin_reader_installed (bool): Whether stdin reader is installed.
    """

    __slots__ = ["_stdin_fd", "_stdout_fd", "_orig_term_attrs", "_resize_handler_installed", "_stdin_reader_installed"]

    def __init__(self) -> None:
        self._stdin_fd: int = sys.stdin.fileno()
        self._stdout_fd: int = sys.stdout.fileno()

        self._orig_term_attrs: Optional[list] = None

        self._resize_handler_installed: bool = False
        self._stdin_reader_installed: bool = False

    def enter_raw(self) -> None:
        """Put the terminal into raw mode.

        Returns:
            None
        """
        self._orig_term_attrs = termios.tcgetattr(self._stdin_fd)
        tty.setraw(self._stdin_fd)

    def exit_raw(self) -> None:
        """Restore the terminal to its previous mode (reverts "enter_raw").

        Returns:
            None
        """
        if self._orig_term_attrs is not None:
            termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._orig_term_attrs)
            self._orig_term_attrs = None

    def install_input_reader(self, loop: Any, on_bytes: Callable[[bytes], None], on_close: Callable[[], None]) -> None:
        """Start reading from stdin and route incoming bytes to callbacks (connected to the manager handler).

        Args:
            loop (Any): The asyncio event loop instance used to register readers/tasks.
            on_bytes (Callable[[bytes], None]): Callback to handle received input bytes.
            on_close (Callable[[], None]): Callback to handle stdin closing or errors.

        Returns:
            None
        """
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
        """Stop reading stdin previously configured by "install_input_reader".

        Args:
            loop (Any): The asyncio event loop instance used to deregister.

        Returns:
            None
        """
        if not self._stdin_reader_installed:
            return

        try:
            loop.remove_reader(self._stdin_fd)
        except Exception:
            pass

        self._stdin_reader_installed = False

    def write_stdout(self, data: bytes) -> None:
        """Write bytes to stdout.

        Args:
            data (bytes): Bytes to write to stdout.

        Returns:
            None
        """
        os.write(self._stdout_fd, data)

    def watch_resize(self, loop: Any, cb: Callable[[int, int], None]) -> None:
        """Start monitoring terminal resize events.

        Args:
            loop (Any): The asyncio event loop instance used to register signal handlers or callbacks.
            cb (Callable[[int, int], None]): Callback to handle the resize.

        Returns:
            None
        """

        def _emit_resize() -> None:
            cols, rows = get_terminal_size_unix()
            cb(cols, rows)

        try:
            loop.add_signal_handler(signal.SIGWINCH, _emit_resize)
        except Exception:
            signal.signal(signal.SIGWINCH, lambda *_: _emit_resize())

        self._resize_handler_installed = True
        _emit_resize()

    def unwatch_resize(self, loop: Any) -> None:
        """Stop monitoring terminal resize events.

        Args:
            loop (Any): The asyncio event loop instance used to deregister signal handlers or callbacks.

        Returns:
            None
        """
        if not self._resize_handler_installed:
            return

        try:
            loop.remove_signal_handler(signal.SIGWINCH)
        except Exception:
            pass

        self._resize_handler_installed = False
