import asyncio
import ctypes
import msvcrt
import os
import sys
from ctypes import wintypes
import time
from typing import Any, Optional

import pywintypes
import win32file
import win32pipe
from docker import DockerClient

from ....foundation.manager.terminal.Terminal import Terminal
from ....foundation.manager.terminal.terminal_utils import get_terminal_size_windows


def _set_raw_console_mode(fd: int):
    handle = msvcrt.get_osfhandle(fd)
    mode = wintypes.DWORD()
    if not ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return None, None

    old_mode = mode.value

    new_mode = old_mode
    new_mode &= ~0x0004  # ENABLE_ECHO_INPUT
    new_mode &= ~0x0002  # ENABLE_LINE_INPUT
    new_mode &= ~0x0001  # ENABLE_PROCESSED_INPUT

    if not ctypes.windll.kernel32.SetConsoleMode(handle, new_mode):
        return None, None

    return handle, old_mode


def _restore_console_mode(handle, old_mode):
    if handle is None:
        return

    ctypes.windll.kernel32.SetConsoleMode(handle, old_mode)


class DockerNPipeTerminal(Terminal):
    __slots__ = ["client", "exec_id", "_check_opened_task", "_pipe_handle", "_term_handle", "_orig_term_attrs"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str):
        super().__init__(handler)

        self.client: DockerClient = client
        self.exec_id: str = exec_id

        self._check_opened_task: Optional[asyncio.Task] = None

        self._pipe_handle: Optional[int] = None
        self._term_handle = None
        self._orig_term_attrs = None

    def _start_external(self) -> None:
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        self._pipe_handle = self.handler._handle.handle
        win32pipe.SetNamedPipeHandleState(self._pipe_handle, 0x00000001, None, None)

        # To get CTRL+C working inside
        self._term_handle, self._orig_term_attrs = _set_raw_console_mode(stdin_fd)

        self._loop.create_task(self._stdin_to_external())
        self._loop.create_task(self._external_to_stdout(stdout_fd))

    @staticmethod
    def _npipe_write(handle: int, data: bytes) -> None:
        if not data:
            return

        try:
            win32file.WriteFile(handle, data)
        except pywintypes.error as e:
            raise e


    # second-code mapping (after '\x00' or '\xe0') -> ANSI escape sequence
    _SPECIAL_TO_ANSI = {
        'H': b'\x1b[A',  # Up
        'P': b'\x1b[B',  # Down
        'M': b'\x1b[C',  # Right
        'K': b'\x1b[D',  # Left
        'G': b'\x1b[H',  # Home
        'O': b'\x1b[F',  # End
        'R': b'\x1b[2~', # Insert
        'S': b'\x1b[3~', # Delete
        'I': b'\x1b[5~', # Page Up
        'Q': b'\x1b[6~', # Page Down
    }

    def read_console_interruptible(self) -> bytes:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()  # unicode char or prefix for special keys

            if ch in ('\x00', '\xe0'):
                code = msvcrt.getwch()  # second part
                return self._SPECIAL_TO_ANSI.get(code, b'')  # ignore unhandled specials

            # best-effort encode to UTF-8
            return ch.encode('utf-8', errors='replace')
        else:
            return b""


    async def _stdin_to_external(self) -> None:
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, self.read_console_interruptible)
            except OSError:
                self.close()
                break

            if not data:
                continue

            try:
                await self._loop.run_in_executor(None, self._npipe_write, self._pipe_handle, data)
            except Exception:
                self.close()
                break

    @staticmethod
    def _npipe_read(handle: int, size: int) -> bytes:
        try:
            _, data = win32file.ReadFile(handle, size, None)
            return data
        except pywintypes.error as e:
            if e.winerror in (232, 233):
                return b""
            raise e

    async def _external_to_stdout(self, stdout_fd: int) -> None:
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, self._npipe_read, self._pipe_handle, 4096)
            except Exception:
                self.close()
                break

            if not data:
                continue

            try:
                await self._loop.run_in_executor(None, os.write, stdout_fd, data)
            except OSError:
                self.close()
                break

    def _on_close(self) -> None:
        for task in asyncio.all_tasks(self._loop):
            task.cancel()
            task._log_destroy_pending = False

        if self._term_handle is not None:
            _restore_console_mode(self._term_handle, self._orig_term_attrs)

        if self._pipe_handle is not None:
            try:
                win32file.CloseHandle(self._pipe_handle)
            except pywintypes.error:
                pass
            self._pipe_handle = None

    def _resize_terminal(self) -> None:
        w, h = get_terminal_size_windows()
        self.client.api.exec_resize(self.exec_id, height=h, width=w)
