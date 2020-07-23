import json
import signal

import pyuv
from kubernetes.stream.ws_client import RESIZE_CHANNEL

from .Terminal import Terminal
from ...utils import exec_by_platform


class SocketTerminal(Terminal):
    def _start_external(self):
        self._external_tty = pyuv.Timer(self._loop)
        self._external_tty.start(self._handle_external_tty(), 0, 0.001)

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
            data = None
            if self.handler.peek_stdout():
                data = self.handler.read_stdout()
            if self.handler.peek_stderr():
                data = self.handler.read_stderr()

            if data:
                self._system_stdout.write(data.encode('utf-8'))

                if data.strip() == 'exit':
                    self.close()

        return handle_external_tty

    def _handle_resize_terminal(self):
        def resize_terminal(signal_handle, signal_num):
            def resize_unix():
                import shutil
                return shutil.get_terminal_size((0, 0))

            def resize_win():
                return 0, 0

            h, w = exec_by_platform(resize_unix, resize_win, resize_unix)
            print("Found size", w, h)
            self.handler.write_channel(RESIZE_CHANNEL, json.dumps({"Height": h, "Width": w}))

        self._resize_signal = pyuv.Signal(self._loop)
        self._resize_signal.start(resize_terminal, signal.SIGWINCH)

        return resize_terminal
