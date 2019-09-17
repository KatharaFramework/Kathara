import argparse

from ..foundation.command.Command import Command


class CheckCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)
        
        parser = argparse.ArgumentParser(
            prog='kathara check',
            description='Check your system environment.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parser.parse_args(argv)

        # Docker Version
        # Settings.check
        # Prova a lanciare hello world
        # Python Version
        # Kathara Version