import pyuv

from .Terminal import Terminal


class SocketTerminal(Terminal):
    def _start_external(self):
        self._external_tty = pyuv.Timer(self._loop)
        self._external_tty.start(self._handle_external_tty(), 1, 1)

    def _on_close(self):
        pass

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self.handler.write_stdin(data)

        return write_on_external_tty

    def _handle_external_tty(self):
        def handle_external_tty(timer_handle):
            data = self.handler.read_stdout()

            if data:
                self._system_stdout.write(data)

                if data.decode('utf-8').strip() == 'exit':
                    self.close()
            else:
                self.close()

        return handle_external_tty
