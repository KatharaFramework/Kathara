from typing import Any

from docker import DockerClient

from .session.DockerTTYTerminalSession import DockerTTYTerminalSession
from ....foundation.manager.terminal.console.UnixConsoleAdapter import UnixConsoleAdapter
from ....foundation.manager.terminal.core.TerminalRunner import TerminalRunner


class DockerTTYTerminal(object):
    __slots__ = ["_runner"]

    def __init__(self, handler: Any, client: DockerClient, exec_id: str) -> None:
        console = UnixConsoleAdapter()
        session = DockerTTYTerminalSession(handler=handler, client=client, exec_id=exec_id)
        self._runner = TerminalRunner(console=console, session=session)

    def start(self) -> None:
        self._runner.start()
