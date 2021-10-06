import argparse
from typing import List

from .LcleanCommand import LcleanCommand
from .LstartCommand import LstartCommand
from ... import utils
from ...foundation.cli.command.Command import Command
from ...strings import strings, wiki_description


class LrestartCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara lrestart',
            description=strings['lrestart'],
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
            "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=True,
            help='Start the lab without opening terminal windows.'
        )
        group.add_argument(
            "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the lab opening terminal windows.'
        )
        group.add_argument(
            "--privileged",
            action="store_const",
            const=True,
            required=False,
            help='Start the devices in privileged mode. MUST BE ROOT FOR THIS OPTION.'
        )
        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        self.parser.add_argument(
            '-F', '--force-lab',
            dest='force_lab',
            required=False,
            action='store_true',
            help='Force the lab to start without a lab.conf or lab.dep file.'
        )
        self.parser.add_argument(
            '-l', '--list',
            required=False,
            action='store_true',
            help='Show information about running devices after the lab has been started.'
        )
        self.parser.add_argument(
            '-o', '--pass',
            dest='options',
            metavar="OPTION",
            nargs='*',
            required=False,
            help="Apply options to all devices of a lab during startup."
        )
        self.parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        self.parser.add_argument(
            '-H', '--no-hosthome',
            dest="no_hosthome",
            action="store_const",
            const=False,
            help='/hosthome dir will not be mounted inside the devices.'
        )
        self.parser.add_argument(
            '-S', '--no-shared',
            dest="no_shared",
            action="store_const",
            const=False,
            help='/shared dir will not be mounted inside the devices.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)

        lclean_argv = ['-d', args['directory']] if args['directory'] else []

        LcleanCommand().run(lab_path, lclean_argv)
        LstartCommand().run(lab_path, argv)
