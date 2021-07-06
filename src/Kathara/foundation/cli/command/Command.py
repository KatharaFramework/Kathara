from abc import ABC, abstractmethod

from ..CliArgs import CliArgs


class Command(ABC):
    __slots__ = ['parser']

    def __init__(self):
        pass

    @abstractmethod
    def run(self, current_path, argv):
        raise NotImplementedError("You must implement `run` method.")

    def parse_args(self, argv):
        args = self.parser.parse_args(argv)
        CliArgs.get_instance().args = vars(args)

    @staticmethod
    def get_args():
        return CliArgs.get_instance().args
