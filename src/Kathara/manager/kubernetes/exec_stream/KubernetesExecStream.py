from collections.abc import Iterator

from ....foundation.manager.exec_stream.IExecStream import IExecStream


class KubernetesExecStream(IExecStream):
    """Kubernetes-specific class for handling the commands stream exec.

    Attributes:
        _stream (Generator): The generator yielding the output of the stream exec.
        _stream_api_object (Any): The specific API object to interact with the underlying stream.
    """

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
        return int(self._stream_api_object.returncode)
