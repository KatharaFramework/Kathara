import argparse

from ..foundation.command.Command import Command
from ..controller.Controller import Controller


class ListCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara list',
            description='Show running Kathara machines.'
        )

        parser.add_argument(
            'machine_name',
            help='Shows only info about specified machine.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        if args.machine_name:
            print(Controller.get_instance().get_machine_info(args.machine_name))
        else:
            streamGenerator = Controller.get_instance().get_info_stream()

            print(next(streamGenerator))
