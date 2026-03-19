from typing import Any

from docker import DockerClient

from .session.DockerNPipeTerminalSession import DockerNPipeSession
from ....foundation.manager.terminal.console.WindowsConsoleAdapter import WindowsConsoleAdapter
from ....foundation.manager.terminal.core.IConsoleAdapter import IConsoleAdapter
from ....foundation.manager.terminal.core.ITerminalSession import ITerminalSession
from ....foundation.manager.terminal.core.TerminalRunner import TerminalRunner


class DockerNPipeTerminal(object):
    """High-level terminal runner for Docker over Named Pipes on Windows.

    Args:
        handler (Any): The exec session handler.
        client (DockerClient): Docker client instance.
        exec_id (int): Docker exec ID identifying the running exec session.
    """

    __slots__ = ["_handler", "_runner"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str) -> None:
        console: IConsoleAdapter = WindowsConsoleAdapter()
        session: ITerminalSession = DockerNPipeSession(handler=handler, client=client, exec_id=exec_id)

        self._handler: Any = handler
        self._runner: TerminalRunner = TerminalRunner(console=console, session=session)

    def start(self) -> None:
        """Start the interactive terminal session.

        Returns:
            None
        """
        self._runner.start()

        # Force close the underlying object
        try:
            self._handler._response.close()
        except Exception:
            pass
