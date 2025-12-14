import asyncio
import ctypes
from ctypes import wintypes
from typing import Any, Optional, Dict, Tuple, Callable

from ..core.IConsoleAdapter import IConsoleAdapter

STD_INPUT_HANDLE: int = -10
STD_OUTPUT_HANDLE: int = -11

# Data structures for the Win32 Input Events
KEY_EVENT: int = 0x0001
WINDOW_BUFFER_SIZE_EVENT: int = 0x0004


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", wintypes.WCHAR),
        ("dwControlKeyState", wintypes.DWORD),
    ]


class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]


class WINDOW_BUFFER_SIZE_RECORD(ctypes.Structure):
    _fields_ = [("dwSize", COORD)]


class EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("KeyEvent", KEY_EVENT_RECORD),
        ("WindowBufferSize", WINDOW_BUFFER_SIZE_RECORD),
    ]


class INPUT_RECORD(ctypes.Structure):
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("Event", EVENT_UNION),
    ]


# Virtual Key Codes
ANSI_ESC: str = "\x1b["
KEYCODES: Dict[int, str] = {
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


class WindowsConsoleAdapter(IConsoleAdapter):
    __slots__ = ["_term_handle", "_orig_mode", "_stdout_handle", "_input_task", "_resize_cb"]

    def __init__(self) -> None:
        self._term_handle: Optional[int] = None
        self._orig_mode: Optional[int] = None

        self._stdout_handle: Optional[int] = None

        self._input_task: Optional[asyncio.Task] = None
        self._resize_cb: Optional[Callable[[int, int], None]] = None

    @staticmethod
    def _set_raw_console_mode() -> Tuple[Optional[int], Optional[int]]:
        handle = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
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

    @staticmethod
    def _restore_console_mode(handle: int, old_mode: int) -> None:
        ctypes.windll.kernel32.SetConsoleMode(handle, old_mode)

    def enter_raw(self) -> None:
        self._term_handle, self._orig_mode = self._set_raw_console_mode()
        self._stdout_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    def exit_raw(self) -> None:
        if self._term_handle is not None and self._orig_mode is not None:
            self._restore_console_mode(self._term_handle, self._orig_mode)

        self._term_handle = None
        self._orig_mode = None

    def _read_win_console_event(self) -> bytes:
        if self._term_handle is None:
            return b""

        rec = INPUT_RECORD()
        nread = wintypes.DWORD()
        # Peek the buffer to avoid blocking read
        ok = ctypes.windll.kernel32.PeekConsoleInputW(self._term_handle, ctypes.byref(rec), 1, ctypes.byref(nread))
        if not ok or nread.value == 0:
            return b""
        # Force the read to consume the buffer events
        ctypes.windll.kernel32.ReadConsoleInputW(self._term_handle, ctypes.byref(rec), 1, ctypes.byref(nread))

        if rec.EventType == WINDOW_BUFFER_SIZE_EVENT:
            if self._resize_cb is not None:
                size = rec.Event.WindowBufferSize.dwSize
                cols, rows = int(size.X), int(size.Y)
                self._resize_cb(cols, rows)
            return b""

        if rec.EventType == KEY_EVENT:
            kev = rec.Event.KeyEvent
            if not kev.bKeyDown:
                return b""

            # Check if it is a special key
            ansi = KEYCODES.get(int(kev.wVirtualKeyCode))
            if ansi:
                return f"{ANSI_ESC}{ansi}".encode("utf-8")

            # Otherwise return the character
            ch = kev.uChar
            if ch is None:
                return b""
            try:
                return ch.encode("utf-8")
            except Exception:
                return b""

        return b""

    def install_input_reader(self, loop: Any, on_bytes: Callable[[bytes], None], on_close: Callable[[], None]) -> None:
        if self._input_task is not None:
            return

        async def _pump() -> None:
            while True:
                try:
                    data = await loop.run_in_executor(None, self._read_win_console_event)
                except Exception:
                    on_close()
                    break
                
                if not data:
                    continue
                
                try:
                    on_bytes(data)
                except Exception:
                    on_close()
                    break

        self._input_task = loop.create_task(_pump())

    def remove_input_reader(self, loop: Any) -> None:
        if self._input_task is None:
            return

        self._input_task.cancel()
        self._input_task = None

    def write_stdout(self, data: bytes) -> None:
        if self._stdout_handle is None:
            return

        text = data.decode("utf-8")
        buffer = ctypes.create_unicode_buffer(text)
        written = wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.WriteConsoleW(self._stdout_handle, buffer, len(buffer), ctypes.byref(written), None)
        if not ok:
            raise RuntimeError

    def watch_resize(self, loop: Any, cb: Callable[[int, int], None]) -> None:
        # Unused, resize is read from the console events, just install the callback
        self._resize_cb = cb

    def unwatch_resize(self, loop: Any) -> None:
        # Unused, resize is read from the console events
        pass
