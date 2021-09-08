from abc import ABC, abstractmethod
from typing import List, Dict

from ..CliArgs import CliArgs


class Command(ABC):
    __slots__ = ['parser']

    def __init__(self) -> None:
        pass

    @abstractmethod
    def run(self, current_path: str, argv: List[str]) -> None:
        raise NotImplementedError("You must implement `run` method.")

    def parse_args(self, argv: List[str]):
        args = self.parser.parse_args(argv)
        CliArgs.get_instance().args = vars(args)

    @staticmethod
    def get_args() -> Dict[str, str]:
        return CliArgs.get_instance().args
