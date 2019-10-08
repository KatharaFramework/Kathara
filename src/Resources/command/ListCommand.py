import argparse

from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy


class ListCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara list',
            description='Show all running Kathara machines.'
        )

        parser.add_argument(
            '-n', '--name',
            required=False,
            help='Show only information about a specified machine.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        if args.name:
            print(ManagerProxy.get_instance().get_machine_info(args.name))
        else:
            lab_info = ManagerProxy.get_instance().get_lab_info()

            print(next(lab_info))
