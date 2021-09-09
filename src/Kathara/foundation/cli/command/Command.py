from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..CliArgs import CliArgs


class Command(ABC):
    __slots__ = ['parser']

    def __init__(self) -> None:
        pass

    @abstractmethod
    def run(self, current_path: str, argv: List[str]) -> Any:
        raise NotImplementedError("You must implement `run` method.")

    def parse_args(self, argv: List[str]) -> None:
        args = self.parser.parse_args(argv)
        CliArgs.get_instance().args = vars(args)

    @staticmethod
    def get_args() -> Dict[str, Any]:
        return CliArgs.get_instance().args
