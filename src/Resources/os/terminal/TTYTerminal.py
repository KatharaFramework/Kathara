import pyuv

from .Terminal import Terminal


class TTYTerminal(Terminal):
    def _start_external(self):
        self._external_tty = pyuv.TTY(self._loop, self.handler.fileno(), True)
        self._external_tty.start_read(self._handle_external_tty())

    def _on_close(self):
        self._system_stdin.set_mode(0)
