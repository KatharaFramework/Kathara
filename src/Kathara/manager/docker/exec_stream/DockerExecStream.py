from collections.abc import Iterator
from typing import Generator

from docker import DockerClient

from ....foundation.manager.exec_stream.IExecStream import IExecStream


class DockerExecStream(IExecStream):
    """Docker-specific class for handling the commands stream exec

    Attributes:
        _stream (Generator): The generator yielding the output of the stream exec.
        _stream_api_object (Any): The specific API object to interact with the underlying stream.
        _client (DockerClient): The Docker client object to interact with the stream.
    """
    __slots__ = ['_client']

    def __init__(self, stream: Generator, stream_api_object: str, client: DockerClient) -> None:
        super().__init__(stream, stream_api_object)

        self._client: DockerClient = client

    def stream_next(self) -> Iterator:
        """Return the next element from the stream.

        Returns:
            Iterator: The output iterator from the stream.
        """
        return next(self._stream)

    def exit_code(self) -> int:
        """Return the exit code of the execution.

        Returns:
            int: The exit code of the execution.
        """
        return int(self._client.api.exec_inspect(self._stream_api_object)['ExitCode'])
