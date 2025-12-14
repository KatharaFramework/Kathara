import json
from typing import Any, Optional

from kubernetes.stream.ws_client import RESIZE_CHANNEL

from .....foundation.manager.terminal.core.ITerminalSession import ITerminalSession


class KubernetesWSTerminalSession(ITerminalSession):
    def __init__(self, handler: Any, client: Any = None) -> None:
        super().__init__(handler, client)

    def fileno(self) -> Optional[int]:
        return None

    def read(self, n: int = 4096) -> bytes:
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
        if self._closed:
            return

        try:
            self._handler.write_stdin(data)
        except Exception:
            raise

    def resize(self, cols: int, rows: int) -> None:
        if self._closed:
            return

        payload = json.dumps({"Height": rows, "Width": cols})
        try:
            self._handler.write_channel(RESIZE_CHANNEL, payload)
        except Exception:
            raise

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        self._handler.close()
