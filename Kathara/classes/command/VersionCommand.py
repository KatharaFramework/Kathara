import argparse

from ..foundation.command.Command import Command
from ..setting.Setting import KATHARA_VERSION


class VersionCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara version',
            description='Print current version.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parser.parse_args(argv)

        print('Current version: %s.' % KATHARA_VERSION)
