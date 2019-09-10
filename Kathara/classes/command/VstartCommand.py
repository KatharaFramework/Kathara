import argparse

from classes.command.Command import Command


class VstartCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vstart',
            description='Start a new Kathara machine.',
            epilog='Example: kathara vstart --eth 0:A 1:B -n pc1'
        )
        parser.add_argument(
            '-n', '--name',
            required=True,
            help='Name of the machine to be started'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            nargs='+',
            required=True,
            help='Set a specific interface on a collision domain.'
        )
        group = parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=True,
            help='Start the lab without opening terminal windows.'
        )
        group.add_argument(
            "-t", "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the lab opening terminal windows.'
        )
        parser.add_argument(
            '-e',
            '--exec',
            required=False,
            dest='exe',
            nargs='*',
            help='Execute a specific command in the container during startup.'
        )
        parser.add_argument(
            '-M', '--mem',
            required=False,
            help='Limit the amount of RAM available for this container.'
        )
        parser.add_argument(
            '-i', '--image',
            required=False,
            help='Run this container with a specific Docker image.'
        )
        parser.add_argument(
            '-H', '--no-hosthome',
            required=False,
            action='store_true',
            help='/hosthome dir will not be mounted inside the machine.'
        )
        parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application.'
        )
        parser.add_argument(
            '-l', '--hostlab',
            required=False,
            help='Set a path for a lab folder to search the specified machine.'
        )
        parser.add_argument(
            '-p', '--print',
            dest='print_only',
            required=False,
            action='store_true',
            help='Print command used to start the container (dry run).'
        )
        parser.add_argument(
            '--bridged',
            required=False,
            action='store_true',
            help='Adds a bridge interface to the container.'
        )
        parser.add_argument(
            '--port',
            required=False,
            help='Choose a port number to map to the internal port 3000 of the container.'
        )
        parser.add_argument(
            '--shell',
            required=False,
            help='Set the shell (sh, bash, etc.) that should be used inside the container.'
        )

        self.parser = parser

    def run(self, argv):
        args = self.parser.parse_args(argv)

        print('Sta tranquillo che la eseguo sta macchina!')
        print(args)
