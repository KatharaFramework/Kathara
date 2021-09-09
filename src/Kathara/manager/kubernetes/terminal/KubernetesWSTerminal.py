import json
import signal
from typing import Callable

import pyuv
from kubernetes.stream.ws_client import RESIZE_CHANNEL

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_windows
from ....utils import exec_by_platform


class KubernetesWSTerminal(Terminal):
    def _start_external(self) -> None:
        self._external_terminal = pyuv.Timer(self._loop)
        self._external_terminal.start(self._read_external_terminal(), 0, 0.001)

    def _on_close(self) -> None:
        def unix_close():
            self._system_stdin.set_mode(0)

            self._resize_signal.close()

        exec_by_platform(unix_close, lambda: None, unix_close)

    def _write_on_external_terminal(self) -> Callable:
        def write_on_external_terminal(handle, data, error):
            self.handler.write_stdin(data)

        return write_on_external_terminal

    def _read_external_terminal(self) -> Callable:
        def read_external_terminal(timer_handle):
            if not self.handler.is_open() and not self._external_terminal.closed:
                self.close()
                return

            data = None
            if self.handler.peek_stdout():
                data = self.handler.read_stdout()
            elif self.handler.peek_stderr():
                data = self.handler.read_stderr()

            if data:
                self._system_stdout.write(data.encode('utf-8'))

                if data.strip() == '\r\nexit\r\n':
                    self.close()

        return read_external_terminal

    def _resize_terminal(self) -> None:
        def resize_unix():
            def resize_terminal(signal_handle, signal_num):
                w, h = self._system_stdin.get_winsize()
                self.handler.write_channel(RESIZE_CHANNEL, json.dumps({"Height": h, "Width": w}))

            self._resize_signal = pyuv.Signal(self._loop)
            self._resize_signal.start(resize_terminal, signal.SIGWINCH)

            # Run first time to set the proper terminal size
            resize_terminal(None, None)

        def resize_windows():
            w, h = get_terminal_size_windows()
            self.handler.write_channel(RESIZE_CHANNEL, json.dumps({"Height": h, "Width": w}))

        exec_by_platform(resize_unix, resize_windows, resize_unix)
