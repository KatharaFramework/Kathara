import argparse

from classes.command.Command import Command


class VcleanCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vclean',
            description='Cleanup Kathara processes and configurations.',
            epilog="Example: kathara vclean pc1"
        )
        parser.add_argument(
            'machine_name',
            help='Name of the machine to be cleaned'
        )

        self.parser = parser

    def run(self, argv):
        args = self.parser.parse_args(argv)

        print('Sta tranquillo che la cleano sta macchina!')
        print(args)
