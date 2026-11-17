from typing import Any

from podman import PodmanClient

from .session.PodmanTTYTerminalSession import PodmanTTYTerminalSession
from ....foundation.manager.terminal.console.UnixConsoleAdapter import UnixConsoleAdapter
from ....foundation.manager.terminal.core.IConsoleAdapter import IConsoleAdapter
from ....foundation.manager.terminal.core.ITerminalSession import ITerminalSession
from ....foundation.manager.terminal.core.TerminalRunner import TerminalRunner


class PodmanTTYTerminal(object):
    """High-level terminal runner for Podman over TTY sessions on Unix platforms.

    Args:
        handler (Any): The hijacked socket returned by `PodmanMachine.connect()`.
        client (PodmanClient): The podman-py low-level API client (`PodmanClient.api`).
        exec_id (str): Podman exec ID identifying the running exec session.
    """

    __slots__ = ["_session", "_runner", "libpodCompat"]

    def __init__(self, handler: Any, client: PodmanClient, exec_id: str) -> None:
        console: IConsoleAdapter = UnixConsoleAdapter()
        session: ITerminalSession = PodmanTTYTerminalSession(handler=handler, client=client, exec_id=exec_id)

        self._session: ITerminalSession = session
        self._runner: TerminalRunner = TerminalRunner(console=console, session=session)

    def start(self) -> None:
        """Start the interactive terminal session.

        Returns:
            None
        """
        try:
            self._runner.start()
        finally:
            # Release the hijacked socket back to the urllib3 pool.
            # Idempotent: PodmanTTYTerminalSession.close() guards on self._closed.
            self._session.close()