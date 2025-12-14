from abc import ABC, abstractmethod
from typing import Any, Optional


class ITerminalSession(ABC):
    __slots__ = ['_handler', '_client', '_closed']

    def __init__(self, handler: Any, client: Any) -> None:
        self._handler: Any = handler
        self._client: Optional[Any] = client

        self._closed: bool = False

    def fileno(self) -> Optional[int]:
        raise NotImplementedError

    @abstractmethod
    def read(self, n: int = 4096) -> bytes:
        raise NotImplementedError("You must implement `read` method.")

    @abstractmethod
    def write(self, data: bytes) -> None:
        raise NotImplementedError("You must implement `write` method.")

    @abstractmethod
    def resize(self, cols: int, rows: int) -> None:
        raise NotImplementedError("You must implement `resize` method.")

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError("You must implement `close` method.")
