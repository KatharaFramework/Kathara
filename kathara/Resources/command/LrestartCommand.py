import argparse

from .LcleanCommand import LcleanCommand
from .LstartCommand import LstartCommand
from .. import utils
from ..foundation.command.Command import Command


class LrestartCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lrestart',
            description='Restart a Kathara lab.'
        )

        group = parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "-n", "--noterminals",
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
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            '-F', '--force-lab',
            dest='force_lab',
            required=False,
            action='store_true',
            help='Force the lab to start without a lab.conf or lab.dep file.'
        )
        parser.add_argument(
            '-l', '--list',
            required=False,
            action='store_true',
            help='Show a list of running containers after the lab has been started.'
        )
        parser.add_argument(
            '-o', '--pass',
            dest='options',
            nargs='*',
            required=False,
            help="Pass options to vstart. Options should be a list of double quoted strings, "
                 "like '--pass \"mem=64m\" \"image=kathara/netkit_base\"'."
        )
        parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        parser.add_argument(
            '-c', '--counter',
            required=False,
            help='Start from a specific network counter '
                 '(overrides whatever was previously initialized).'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        lclean_argv = ['-d', args.directory] if args.directory else []

        LcleanCommand().run(lab_path, lclean_argv)
        LstartCommand().run(lab_path, argv)
