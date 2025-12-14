from typing import Any

from docker import DockerClient

from .session.DockerNPipeTerminalSession import DockerNPipeSession
from ....foundation.manager.terminal.console.WindowsConsoleAdapter import WindowsConsoleAdapter
from ....foundation.manager.terminal.core.TerminalRunner import TerminalRunner


class DockerNPipeTerminal(object):
    __slots__ = ["_runner"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str) -> None:
        console = WindowsConsoleAdapter()
        session = DockerNPipeSession(handler=handler, client=client, exec_id=exec_id)
        self._runner = TerminalRunner(console=console, session=session)

    def start(self) -> None:
        self._runner.start()

    def close(self) -> None:
        self._runner.close()
