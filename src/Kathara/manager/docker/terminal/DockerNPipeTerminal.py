import asyncio
import msvcrt
import os
import sys
from typing import Any, Optional

import win32pipe
from docker import DockerClient
from docker.errors import APIError

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_windows


class DockerNPipeTerminal(Terminal):
    __slots__ = ["client", "exec_id", "_check_opened_task", "_external_fd"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str):
        super().__init__(handler)

        self.client: DockerClient = client
        self.exec_id: str = exec_id

        self._check_opened_task: Optional[asyncio.Task] = None
        self._external_fd: Optional[int] = None

    def _start_external(self) -> None:
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        self._external_fd = self._convert_pipe_to_fd()

        self._loop.create_task(self._stdin_to_external(stdin_fd))
        self._loop.create_task(self._external_to_stdout(stdout_fd))
        self._check_opened_task = self._loop.create_task(self._watch_exec_opened())

    def _convert_pipe_to_fd(self) -> int:
        handle_id = self.handler._handle.handle
        win32pipe.SetNamedPipeHandleState(handle_id, 0x00000001, None, None)
        handle_fd = msvcrt.open_osfhandle(handle_id, os.O_APPEND)
        return handle_fd

    async def _stdin_to_external(self, stdin_fd: int) -> None:
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, os.read, stdin_fd, 4096)
            except OSError:
                self.close()
                break

            if not data:
                self.close()
                break

            if self._external_fd is None:
                self.close()
                break

            try:
                await self._loop.run_in_executor(None, os.write, self._external_fd, data)
            except OSError:
                self.close()
                break

    async def _external_to_stdout(self, stdout_fd: int) -> None:
        while not self._closed:
            if self._external_fd is None:
                self.close()
                break

            try:
                data = await self._loop.run_in_executor(None, os.read, self._external_fd, 4096)
            except OSError:
                self.close()
                break

            if not data:
                self.close()
                break

            try:
                await self._loop.run_in_executor(None, os.write, stdout_fd, data)
            except OSError:
                self.close()
                break

            if data == b"\r\nexit\r\n":
                self.close()
                break

    def _on_close(self) -> None:
        if self._check_opened_task is not None and not self._check_opened_task.done():
            self._check_opened_task.cancel()

        if self._external_fd is not None:
            try:
                os.close(self._external_fd)
            except OSError:
                pass

            self._external_fd = None
            self._closed = True

    def _resize_terminal(self) -> None:
        w, h = get_terminal_size_windows()
        self.client.api.exec_resize(self.exec_id, height=h, width=w)

    async def _watch_exec_opened(self) -> None:
        try:
            await self._check_exec_once()
            while not self._closed:
                await asyncio.sleep(5)
                await self._check_exec_once()
        except asyncio.CancelledError:
            pass

    async def _check_exec_once(self) -> None:
        def _inspect():
            return self.client.api.exec_inspect(self.exec_id)

        try:
            await self._loop.run_in_executor(None, _inspect)
        except APIError:
            self.close()
