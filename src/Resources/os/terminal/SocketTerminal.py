import pyuv

from .Terminal import Terminal
from ...utils import exec_by_platform


class SocketTerminal(Terminal):
    def _start_external(self):
        self._external_tty = pyuv.Timer(self._loop)
        self._external_tty.start(self._handle_external_tty(), 0.1, 0.1)

    def _on_close(self):
        def unix_close():
            self._system_stdin.set_mode(0)

        exec_by_platform(unix_close, lambda: None, unix_close)

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self.handler.write_stdin(data)

        return write_on_external_tty

    def _handle_external_tty(self):
        def handle_external_tty(timer_handle):
            if self.handler.peek_stdout():
                data = self.handler.read_stdout()
                self._system_stdout.write(data.encode('utf-8'))

                if data.strip() == 'exit':
                    self.close()

        return handle_external_tty
