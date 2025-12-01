import asyncio
import json
import os
import signal
import sys
from typing import Optional

from kubernetes.stream.ws_client import RESIZE_CHANNEL

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_windows, get_terminal_size_unix
from ....utils import exec_by_platform


class KubernetesWSTerminal(Terminal):
    __slots__ = ["_reader_task", "_stdin_task"]

    def __init__(self, handler):
        super().__init__(handler)

        self._reader_task: Optional[asyncio.Task] = None
        self._stdin_task: Optional[asyncio.Task] = None

    def _start_external(self) -> None:
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()

        self._stdin_task = self._loop.create_task(self._stdin_to_ws(stdin_fd))
        self._reader_task = self._loop.create_task(self._poll_ws_output(stdout_fd))

    async def _stdin_to_ws(self, stdin_fd: int) -> None:
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, os.read, stdin_fd, 4096)
            except OSError:
                self.close()
                break

            if not data:
                self.close()
                break

            try:
                self.handler.write_stdin(data)
            except Exception:
                self.close()
                break

    async def _poll_ws_output(self, stdout_fd: int) -> None:
        try:
            while not self._closed:
                if not self.handler.is_open():
                    self.close()
                    break

                data = None
                try:
                    if self.handler.peek_stdout():
                        data = self.handler.read_stdout()
                    elif self.handler.peek_stderr():
                        data = self.handler.read_stderr()
                except Exception:
                    self.close()
                    break

                if data:
                    try:
                        await self._loop.run_in_executor(None, os.write, stdout_fd, data.encode("utf-8"))
                    except OSError:
                        self.close()
                        break

                    if data.strip() == "\r\nexit\r\n":
                        self.close()
                        break
        except asyncio.CancelledError:
            pass

    def _on_close(self) -> None:
        if self._stdin_task is not None and not self._stdin_task.done():
            self._stdin_task.cancel()

        if self._reader_task is not None and not self._reader_task.done():
            self._reader_task.cancel()

        def unix_close():
            try:
                self._loop.remove_signal_handler(signal.SIGWINCH)
            except Exception:
                pass

        exec_by_platform(unix_close, lambda: None, unix_close)

    def _resize_terminal(self) -> None:
        def resize_unix():
            def resize():
                cols, rows = get_terminal_size_unix()
                self.handler.write_channel(RESIZE_CHANNEL, json.dumps({"Height": rows, "Width": cols}))

            try:
                self._loop.add_signal_handler(signal.SIGWINCH, resize)
            except Exception:
                signal.signal(signal.SIGWINCH, lambda *_: resize())

            resize()

        def resize_windows():
            w, h = get_terminal_size_windows()
            self.handler.write_channel(RESIZE_CHANNEL, json.dumps({"Height": h, "Width": w}))

        exec_by_platform(resize_unix, resize_windows, resize_unix)
