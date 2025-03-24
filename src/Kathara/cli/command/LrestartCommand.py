import argparse
from typing import List

from .LcleanCommand import LcleanCommand
from .LstartCommand import LstartCommand
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
            help='Show a help message and exit.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=True,
            help='Start the network scenario without opening terminal windows.'
        )
        group.add_argument(
            "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the network scenario opening terminal windows.'
        )
        self.parser.add_argument(
            "--privileged",
            action="store_const",
            const=True,
            required=False,
            help='Start the devices in privileged mode. MUST BE ROOT FOR THIS OPTION.'
        )
        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the network scenario.'
        )
        self.parser.add_argument(
            '-F', '--force-lab',
            dest='force_lab',
            required=False,
            action='store_true',
            help='Force the network scenario to start without a lab.conf or lab.dep file.'
        )
        self.parser.add_argument(
            '-l', '--list',
            required=False,
            action='store_true',
            help='Show information about running devices after the network scenario has been started.'
        )
        self.parser.add_argument(
            '-o', '--pass',
            dest='global_machine_metadata',
            metavar="METADATA",
            nargs='*',
            required=False,
            help="Apply metadata to all devices of a network scenario during startup."
        )
        self.parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        hosthome_group = self.parser.add_mutually_exclusive_group(required=False)
        hosthome_group.add_argument(
            '--no-hosthome', '-H',
            dest="hosthome_mount",
            action="store_const",
            const=False,
            help='Do not mount "/hosthome" directory inside devices.'
        )
        hosthome_group.add_argument(
            '--hosthome',
            dest="hosthome_mount",
            action="store_const",
            const=True,
            help='Mount "/hosthome" directory inside devices.'
        )
        shared_group = self.parser.add_mutually_exclusive_group(required=False)
        shared_group.add_argument(
            '--no-shared', '-S',
            dest="shared_mount",
            action="store_const",
            const=False,
            help='Do not mount "/shared" directory inside devices.'
        )
        shared_group.add_argument(
            '--shared',
            dest="shared_mount",
            action="store_const",
            const=True,
            help='Mount "/shared" directory inside devices.'
        )
        self.parser.add_argument(
            '--exclude',
            dest='excluded_machines',
            metavar='DEVICE_NAME',
            nargs='+',
            default=[],
            help='Exclude specified devices.'
        )
        self.parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Restarts only specified devices.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        lclean_argv = ['-d', args['directory']] if args['directory'] else []

        if args['machine_name']:
            lclean_argv.extend(args['machine_name'])
        if args['excluded_machines']:
            lclean_argv.extend(['--exclude'] + args['excluded_machines'])

        LcleanCommand().run(current_path, lclean_argv)
        LstartCommand().run(current_path, argv)

        return 0
