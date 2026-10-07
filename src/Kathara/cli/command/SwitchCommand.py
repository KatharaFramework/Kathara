import argparse
import sys
from typing import List

from ... import utils
from ...exceptions import LinkCommandError
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description

# Words which leave the interactive console
EXIT_COMMANDS = ['exit', 'quit', 'logout']


class SwitchCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara switch',
            description=strings['switch'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show a help message and exit.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            '-d', '--directory',
            help='Specify the folder containing the network scenario.',
        )
        group.add_argument(
            '-v', '--vmachine',
            dest="vmachine",
            action="store_true",
            help='The collision domain has been created with vstart command.',
        )
        self.parser.add_argument(
            'cd_name',
            metavar='CD_NAME',
            help='Name of the managed collision domain.'
        )
        self.parser.add_argument(
            'command',
            metavar='COMMAND',
            nargs=argparse.REMAINDER,
            help='Command sent to the collision domain (e.g. `port/print`, `vlan/create 10`, `help`). '
                 'If omitted, an interactive console is opened.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        if args['vmachine']:
            lab = Lab("kathara_vlab")
        else:
            lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
            lab_path = utils.get_absolute_path(lab_path)

            # Load custom 'kathara.conf' if it exists
            self._load_custom_configuration(lab_path)

            try:
                lab = LabParser.parse(lab_path)
            except (Exception, IOError):
                lab = Lab(None, path=lab_path)

        if args['command']:
            return self._exec(lab, args['cd_name'], " ".join(args['command']))

        # Fails before the first prompt if the collision domain cannot be managed
        Kathara.get_instance().get_link_ports(args['cd_name'], lab_hash=lab.hash)

        while True:
            try:
                command = input(f"{args['cd_name']}$ ").strip()
            except (EOFError, KeyboardInterrupt):
                sys.stdout.write("\n")
                break

            if command in EXIT_COMMANDS:
                break

            if command:
                self._exec(lab, args['cd_name'], command)

        return 0

    @staticmethod
    def _exec(lab: Lab, cd_name: str, command: str) -> int:
        try:
            output = Kathara.get_instance().exec_link(cd_name, command, lab_hash=lab.hash)
        except LinkCommandError as e:
            sys.stderr.write(f"{e.code} {e.message}\n")
            return 1

        if output:
            sys.stdout.write(f"{output}\n")

        return 0
