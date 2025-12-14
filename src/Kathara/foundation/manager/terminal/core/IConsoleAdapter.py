from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class IConsoleAdapter(ABC):
    @abstractmethod
    def enter_raw(self) -> None:
        raise NotImplementedError("You must implement `enter_raw` method.")

    @abstractmethod
    def exit_raw(self) -> None:
        raise NotImplementedError("You must implement `exit_raw` method.")

    @abstractmethod
    def install_input_reader(self, loop: Any, on_bytes: Callable[[bytes], None], on_close: Callable[[], None]) -> None:
        raise NotImplementedError("You must implement `install_input_reader` method.")

    @abstractmethod
    def remove_input_reader(self, loop: Any) -> None:
        raise NotImplementedError("You must implement `remove_input_reader` method.")

    @abstractmethod
    def write_stdout(self, data: bytes) -> None:
        raise NotImplementedError("You must implement `write_stdout` method.")

    @abstractmethod
    def watch_resize(self, loop: Any, cb: Callable[[int, int], None]) -> None:
        raise NotImplementedError("You must implement `watch_resize` method.")

    @abstractmethod
    def unwatch_resize(self, loop: Any) -> None:
        raise NotImplementedError("You must implement `unwatch_resize` method.")
