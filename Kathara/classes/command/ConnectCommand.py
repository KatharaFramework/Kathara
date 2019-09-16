import argparse

import utils
from .Command import Command
from ..deployer.Deployer import Deployer


class ConnectCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)
        
        parser = argparse.ArgumentParser(
            prog='kathara connect',
            description='Connect current terminal to a Kathara machine.'
        )

        parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            '-c', '--command',
            required=False,
            help='Specify the command to start the TTY.'
        )
        parser.add_argument(
            'machine_name',
            help='Name of the machine to connect to'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        Deployer.get_instance().connect_tty(lab_hash,
                                            machine_name=args.machine_name,
                                            command=args.command
                                            )
