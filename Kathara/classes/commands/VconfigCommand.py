import argparse

from classes.commands.Command import Command


class VconfigCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vconfig',
            description='Attach network interfaces to running Kathara machines.',
            epilog='Example: kathara vconfig --eth A -n pc1'
        )
        parser.add_argument(
            '-n', '--name',
            required=True,
            help='Name of the machine to be attached with the new interface.'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            nargs='+',
            required=True,
            help='Set a specific interface on a collision domain.'
        )

        self.parser = parser

    def run(self, argv):
        args = self.parser.parse_args(argv)

        print('Sta tranquillo che la addo sta iface!')
        print(args)