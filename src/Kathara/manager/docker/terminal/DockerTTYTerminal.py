import signal
from typing import Any

import pyuv
from docker import DockerClient

from ....foundation.manager.terminal.Terminal import Terminal


class DockerTTYTerminal(Terminal):
    __slots__ = ['client', 'exec_id']

    def __init__(self, handler: Any, client: DockerClient, exec_id: str):
        super().__init__(handler)

        self.client: DockerClient = client
        self.exec_id: str = exec_id

    def _start_external(self) -> None:
        self._external_terminal = pyuv.TTY(self._loop, self.handler.fileno(), True)
        self._external_terminal.start_read(self._read_external_terminal())

    def _on_close(self) -> None:
        self._system_stdin.set_mode(0)

        self._resize_signal.close()

    def _resize_terminal(self) -> None:
        def resize_terminal(signal_handle, signal_num):
            w, h = self._system_stdin.get_winsize()
            self.client.api.exec_resize(self.exec_id, height=h, width=w)

        self._resize_signal = pyuv.Signal(self._loop)
        self._resize_signal.start(resize_terminal, signal.SIGWINCH)

        # Run first time to set the proper terminal size
        resize_terminal(None, None)
