import json
from typing import Any, Optional

from kubernetes.stream.ws_client import RESIZE_CHANNEL

from .....foundation.manager.terminal.core.ITerminalSession import ITerminalSession


class KubernetesWSTerminalSession(ITerminalSession):
    def __init__(self, handler: Any, client: Any = None) -> None:
        super().__init__(handler, client)

    def fileno(self) -> Optional[int]:
        """Return an OS-level file descriptor for the session, if available.

        Returns:
            Optional[int]: The file descriptor, or None if the session cannot be polled via fd-based readiness APIs.
        """
        return None

    def read(self, n: int = 4096) -> bytes:
        """Read up to n bytes from the session output stream.

        Args:
            n (int): Maximum number of bytes to read.

        Returns:
            bytes: Data read from the session.
        """
        if self._closed:
            return b""

        if not self._handler.is_open():
            raise Exception

        data = None
        try:
            if self._handler.peek_stdout():
                data = self._handler.read_stdout()
            elif self._handler.peek_stderr():
                data = self._handler.read_stderr()
        except Exception:
            return b""

        if data is None:
            return b""

        try:
            return data.encode("utf-8")
        except Exception:
            return b""

    def write(self, data: bytes) -> None:
        """Write bytes to the session input stream.

        Args:
            data (bytes): Data to send to the session.

        Returns:
            None
        """
        if self._closed:
            return

        try:
            self._handler.write_stdin(data)
        except Exception as e:
            raise e

    def resize(self, cols: int, rows: int) -> None:
        """Resize the session terminal dimensions.

        Args:
            cols (int): Terminal width in columns.
            rows (int): Terminal height in rows.

        Returns:
            None
        """
        if self._closed:
            return

        payload = json.dumps({"Height": rows, "Width": cols})
        try:
            self._handler.write_channel(RESIZE_CHANNEL, payload)
        except Exception as e:
            raise e

    def close(self) -> None:
        """Close the session and release resources.

        Returns:
            None
        """
        if self._closed:
            return

        self._closed = True
        self._handler.close()
