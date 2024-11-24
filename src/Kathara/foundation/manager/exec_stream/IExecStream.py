from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Generator


class IExecStream(ABC):
    """Interface for handling the commands stream exec

    Attributes:
        _stream (Generator): The generator yielding the output of the stream exec.
        _stream_api_object (Any): The specific API object to interact with the underlying stream.
    """
    __slots__ = ['_stream', '_stream_api_object']

    def __init__(self, stream: Generator, stream_api_object: Any) -> None:
        self._stream: Generator = stream
        self._stream_api_object: Any = stream_api_object

    @abstractmethod
    def stream_next(self) -> Iterator:
        """Return the next element from the stream.

        Returns:
            Iterator: The output iterator from the stream.
        """
        raise NotImplementedError("You must implement `next` method.")

    @abstractmethod
    def exit_code(self) -> int:
        """Return the exit code of the execution.

        Returns:
            int: The exit code of the execution.
        """
        raise NotImplementedError("You must implement `exit_code` method.")

    def __next__(self) -> Iterator:
        """Return the next element from the stream.
        This magic method allows to keep compatibility with the previous API.

        Returns:
            Iterator: The output iterator from the stream.
        """
        return self.stream_next()
