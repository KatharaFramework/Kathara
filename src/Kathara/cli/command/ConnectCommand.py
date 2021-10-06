import argparse
import logging
from typing import List

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...strings import strings, wiki_description


class ConnectCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara connect',
            description=strings['connect'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            '-d', '--directory',
            help='Specify the folder containing the lab.',
        )
        group.add_argument(
            '-v', '--vmachine',
            dest="vmachine",
            action="store_true",
            help='The device has been started with vstart command.',
        )
        self.parser.add_argument(
            '--shell',
            required=False,
            help='Shell that should be used inside the device.'
        )
        self.parser.add_argument(
            '-l', '--logs',
            action="store_true",
            help='Print device startup logs before launching the shell.',
        )
        self.parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            help='Name of the device to connect to.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        if args['vmachine']:
            lab_path = "kathara_vlab"
        else:
            lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
            lab_path = utils.get_absolute_path(lab_path)

        logging.debug("Executing `connect` command in path `%s`..." % lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        Kathara.get_instance().connect_tty(lab_hash, machine_name=args['machine_name'], shell=args['shell'],
                                           logs=args['logs'])
