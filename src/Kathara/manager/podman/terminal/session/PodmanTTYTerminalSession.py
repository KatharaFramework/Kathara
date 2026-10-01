import os
from typing import Any, Optional

from .....foundation.manager.terminal.core.ITerminalSession import ITerminalSession
from ...libpod_compat import LibpodCompat


class PodmanTTYTerminalSession(ITerminalSession):
    """Interactive TTY session for the Podman backend over a hijacked exec socket.

    Mirrors DockerTTYTerminalSession: it wraps the raw bidirectional socket produced
    by an exec hijack and exposes it through the engine-neutral ITerminalSession
    contract (fileno/read/write/resize/close), so TerminalRunner can drive it unchanged.

    Temporary shim: the hijack and resize plumbing lives in libpod_compat because the
    current podman-py release exposes no low-level exec_create / exec_start(socket=True)
    / exec_resize. Once those land upstream (see podman-py #648), the helpers can be
    swapped for the SDK and this class collapses onto the Docker one.

    Args:
        handler (Any): The hijacked exec socket (from exec_start_hijack in connect()).
                       Owned by this session for its whole lifecycle.
        client (Any): The podman-py APIClient, used only to issue the resize request.
        exec_id (str): The exec instance id, required to address the resize endpoint.
    """

    __slots__ = ['_exec_id', '_external_fd', 'libpodCompat']

    def __init__(self, handler: Any, client: Any, exec_id: str) -> None:
        super().__init__(handler, client)

        self._exec_id: str = exec_id
        # Cache the OS-level fd of the hijacked socket; read/write go through it directly.
        self._external_fd: int = handler.fileno()
        self.libpodCompat: LibpodCompat = LibpodCompat(client)

    def fileno(self) -> Optional[int]:
        """Return an OS-level file descriptor for the session, if available.

        Returns:
            Optional[int]: The file descriptor, or None if the session cannot be polled via fd-based readiness APIs.
        """
        return self._external_fd

    def read(self, n: int = 4096) -> bytes:
        """Read up to n bytes from the session output stream.

        Args:
            n (int): Maximum number of bytes to read.

        Returns:
            bytes: Data read from the session.
        """
        if self._closed:
            return b""

        try:
            # TTY stream is raw (stdout/stderr merged, no frame header) -> plain fd read.
            return os.read(self._external_fd, n)
        except OSError:
            # Socket closed underneath us (peer gone) -> signal EOF to the runner.
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

        os.write(self._external_fd, data)

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

        # podman-py has no exec_resize equivalent: hit POST /exec/{id}/resize directly.
        # Note the axis order: the endpoint wants height/width, cols->w, rows->h.
        self.libpodCompat.exec_resize(self._exec_id, cols, rows)

    def close(self) -> None:
        """Close the session and release resources.

        Returns:
            None
        """
        if self._closed:
            return

        self._closed = True

        try:
            # Close the socket OBJECT, not the bare fd: this is what actually releases
            # the urllib3 connection anchored by _hijacked_response. Closing only the fd
            # would leak the pooled connection (pool exhaustion) and risk a double-close
            # of the same fd when the socket is later garbage-collected.
            self._handler.close()
        except OSError:
            pass