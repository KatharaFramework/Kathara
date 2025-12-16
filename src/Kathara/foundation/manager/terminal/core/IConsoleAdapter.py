from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class IConsoleAdapter(ABC):
    """Interface for a platform console adapter. Implementations provide the glue between a manager event loop
    and the underlying platform's console/terminal IO mechanisms."""

    @abstractmethod
    def enter_raw(self) -> None:
        """Put the terminal into raw mode.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `enter_raw` method.")

    @abstractmethod
    def exit_raw(self) -> None:
        """Restore the terminal to its previous mode (reverts "enter_raw").

        Returns:
            None
        """
        raise NotImplementedError("You must implement `exit_raw` method.")

    @abstractmethod
    def install_input_reader(self, loop: Any, on_bytes: Callable[[bytes], None], on_close: Callable[[], None]) -> None:
        """Start reading from stdin and route incoming bytes to callbacks (connected to the manager handler).

        Args:
            loop (Any): The asyncio event loop instance used to register readers/tasks.
            on_bytes (Callable[[bytes], None]): Callback to handle received input bytes.
            on_close (Callable[[], None]): Callback to handle stdin closing or errors.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `install_input_reader` method.")

    @abstractmethod
    def remove_input_reader(self, loop: Any) -> None:
        """Stop reading stdin previously configured by "install_input_reader".

        Args:
            loop (Any): The asyncio event loop instance used to deregister.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `remove_input_reader` method.")

    @abstractmethod
    def write_stdout(self, data: bytes) -> None:
        """Write bytes to stdout.

        Args:
            data (bytes): Bytes to write to stdout.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `write_stdout` method.")

    @abstractmethod
    def watch_resize(self, loop: Any, cb: Callable[[int, int], None]) -> None:
        """Start monitoring terminal resize events.

        Args:
            loop (Any): The asyncio event loop instance used to register signal handlers or callbacks.
            cb (Callable[[int, int], None]): Callback to handle the resize.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `watch_resize` method.")

    @abstractmethod
    def unwatch_resize(self, loop: Any) -> None:
        """Stop monitoring terminal resize events.

        Args:
            loop (Any): The asyncio event loop instance used to deregister signal handlers or callbacks.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `unwatch_resize` method.")
