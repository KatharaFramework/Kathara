import asyncio
import ctypes
import msvcrt
import win32api
import sys
from ctypes import wintypes
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


STD_OUTPUT_HANDLE = -11

# Virtual Key Codes for arrow keys and function keys
ANSI_ESC = "\x1b["
keycodes = {
    # Home/End
    33: "5~",
    34: "6~",
    35: "F",
    36: "H",
    # Arrows
    37: "D",
    38: "A",
    39: "C",
    40: "B",
    45: "2~",
    46: "3~",
    # F-keys
    112: "11~",
    113: "12~",
    114: "13~",
    115: "14~",
    116: "15~",
    117: "17~",
    118: "18~",
    119: "19~",
    120: "20~",
    121: "21~",
    122: "23~",
    123: "24~",
}


# Data structures for the Win32 KeyRecord
KEY_EVENT = 0x0001


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", wintypes.WCHAR),
        ("dwControlKeyState", wintypes.DWORD),
    ]


class _EVENT_UNION(ctypes.Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]


class INPUT_RECORD(ctypes.Structure):
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("Event", _EVENT_UNION),
    ]


class DockerNPipeTerminal(Terminal):
    __slots__ = ["client", "exec_id", "_pipe_handle", "_term_handle", "_orig_term_attrs"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str):
        super().__init__(handler)

        self.client: DockerClient = client
        self.exec_id: str = exec_id

        self._pipe_handle: Optional[int] = None
        self._term_handle = None
        self._orig_term_attrs = None

    def _start_external(self) -> None:
        stdin_fd = sys.stdin.fileno()
        self._pipe_handle = self.handler._handle.handle
        win32pipe.SetNamedPipeHandleState(self._pipe_handle, 0x00000001, None, None)
        self._term_handle, self._orig_term_attrs = _set_raw_console_mode(stdin_fd)

        stdout_fd = win32api.GetStdHandle(STD_OUTPUT_HANDLE)

        self._loop.create_task(self._stdin_to_external())
        self._loop.create_task(self._external_to_stdout(stdout_fd))

    def _read_console_raw(self) -> bytes:
        # Return if no key is pressed
        if not msvcrt.kbhit():
            return b""

        rec = INPUT_RECORD()
        nread = wintypes.DWORD()
        ok = ctypes.windll.kernel32.ReadConsoleInputW(self._term_handle, ctypes.byref(rec), 1, ctypes.byref(nread))
        if not ok or nread.value == 0:
            return b""
        if rec.EventType != KEY_EVENT:
            return b""

        kev = rec.Event.KeyEvent
        if not kev.bKeyDown:
            return b""

        # Check if it is a special key
        ansi_sequence = keycodes.get(kev.wVirtualKeyCode, None)
        if ansi_sequence:
            return f"{ANSI_ESC}{ansi_sequence}".encode("utf-8")

        # Otherwise return the character
        return kev.uChar.encode("utf-8")

    @staticmethod
    def _npipe_write(handle: int, data: bytes) -> None:
        if not data:
            return

        try:
            win32file.WriteFile(handle, data)
        except pywintypes.error as e:
            raise e

    async def _stdin_to_external(self) -> None:
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, self._read_console_raw)
            except Exception:
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
        
    def _write_console_raw(self, fd: int, data: bytes) -> None:
        buffer = ctypes.create_unicode_buffer(data.decode('utf-8'))
        written = wintypes.DWORD(0)
        result = ctypes.windll.kernel32.WriteConsoleW(fd, buffer, len(buffer), ctypes.byref(written), None)
        if not result:
            raise Exception

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
                await self._loop.run_in_executor(None, self._write_console_raw, stdout_fd, data)
            except Exception:
                self.close()
                break

    def _on_close(self) -> None:
        for task in asyncio.all_tasks(self._loop):
            task._log_destroy_pending = False
            task.cancel()

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
