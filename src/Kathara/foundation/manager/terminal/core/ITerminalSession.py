from abc import ABC, abstractmethod
from typing import Any, Optional


class ITerminalSession(ABC):
    """Abstract interface representing an interactive terminal session.
    Instances should wrap a manager session (bidirectional byte stream) with resize support.

    Attributes:
        _handler (Any): A manager-specific handler of the session.
        _client (Optional[Any]): Manager client instance.
        _closed (bool): Boolean flag indicating whether session termination was requested.
    """

    __slots__ = ['_handler', '_client', '_closed']

    def __init__(self, handler: Any, client: Any) -> None:
        self._handler: Any = handler
        self._client: Optional[Any] = client

        self._closed: bool = False

    def fileno(self) -> Optional[int]:
        """Return an OS-level file descriptor for the session, if available.

        Returns:
            Optional[int]: The file descriptor, or None if the session cannot be polled via fd-based readiness APIs.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self, n: int = 4096) -> bytes:
        """Read up to n bytes from the session output stream.

        Args:
            n (int): Maximum number of bytes to read.

        Returns:
            bytes: Data read from the session.
        """
        raise NotImplementedError("You must implement `read` method.")

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Write bytes to the session input stream.

        Args:
            data (bytes): Data to send to the session.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `write` method.")

    @abstractmethod
    def resize(self, cols: int, rows: int) -> None:
        """Resize the session terminal dimensions.

        Args:
            cols (int): Terminal width in columns.
            rows (int): Terminal height in rows.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `resize` method.")

    @abstractmethod
    def close(self) -> None:
        """Close the session and release resources.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `close` method.")
