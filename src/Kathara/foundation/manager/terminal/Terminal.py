import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional


class Terminal(ABC):
    __slots__ = ["handler", "_loop", "_closed"]

    def __init__(self, handler: Any) -> None:
        self.handler: Any = handler
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._closed: bool = False

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._start_external()
        self._resize_terminal()

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def close(self) -> None:
        if self._closed or self._loop is None:
            return

        self._closed = True
        self._on_close()
        self._loop.stop()

    @abstractmethod
    def _start_external(self) -> None:
        pass

    @abstractmethod
    def _on_close(self) -> None:
        pass

    @abstractmethod
    def _resize_terminal(self) -> None:
        pass
