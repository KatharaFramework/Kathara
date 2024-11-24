from abc import ABC, abstractmethod
from typing import List, Dict, Any

from rich.console import Console
from rich.theme import Theme

from ..CliArgs import CliArgs


class Command(ABC):
    __slots__ = ['parser', 'console']

    def __init__(self) -> None:
        self.console: Console = Console(
            theme=Theme({
                "kathara.lab_name": "bold dark_orange3",
                "kathara.lab_description": "bold dark_orange3",
                "kathara.lab_version": "bold dark_orange3",
                "kathara.lab_author": "bold dark_orange3",
                "kathara.lab_email": "bold dark_orange3",
                "kathara.lab_web": "bold dark_orange3",
            })
        )

    @abstractmethod
    def run(self, current_path: str, argv: List[str]) -> int:
        raise NotImplementedError("You must implement `run` method.")

    def parse_args(self, argv: List[str]) -> None:
        args = self.parser.parse_args(argv)
        CliArgs.get_instance().args = vars(args)

    @staticmethod
    def get_args() -> Dict[str, Any]:
        return CliArgs.get_instance().args
