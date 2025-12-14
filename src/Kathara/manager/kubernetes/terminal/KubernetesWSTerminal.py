from typing import Any

from .session.KubernetesWSTerminalSession import KubernetesWSTerminalSession
from ....foundation.manager.terminal.core.TerminalRunner import TerminalRunner
from ....utils import exec_by_platform


class KubernetesWSTerminal(object):
    __slots__ = ["_runner"]

    def __init__(self, handler: Any) -> None:
        session = KubernetesWSTerminalSession(handler)

        def unix():
            from ....foundation.manager.terminal.console.UnixConsoleAdapter import UnixConsoleAdapter
            return UnixConsoleAdapter()

        def windows():
            from ....foundation.manager.terminal.console.WindowsConsoleAdapter import WindowsConsoleAdapter
            return WindowsConsoleAdapter()

        console = exec_by_platform(unix, windows, unix)
        self._runner = TerminalRunner(console=console, session=session)

    def start(self) -> None:
        self._runner.start()
