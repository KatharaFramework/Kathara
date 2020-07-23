import signal

import pyuv

from .Terminal import Terminal
from .terminal_utils import get_terminal_size_linux


class TTYTerminal(Terminal):
    def _start_external(self):
        self._external_tty = pyuv.TTY(self._loop, self.handler.fileno(), True)
        self._external_tty.start_read(self._handle_external_tty())

    def _on_close(self):
        self._system_stdin.set_mode(0)
        self._resize_signal.close()

    def _handle_resize_terminal(self):
        def resize_terminal(signal_handle, signal_num):
            w, h = get_terminal_size_linux()

        self._resize_signal = pyuv.Signal(self._loop)
        self._resize_signal.start(resize_terminal, signal.SIGWINCH)

        resize_terminal(None, None)
