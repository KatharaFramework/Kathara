import argparse

from classes.command.Command import Command
from classes.command.LstartCommand import LstartCommand
from classes.command.LcleanCommand import LcleanCommand


class LrestartCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lrestart',
            description='Restart a Kathara lab'
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
            help='Show a list of running container after the lab has been started.'
        )
        parser.add_argument(
            '-o', '--pass',
            dest='options',
            nargs='*',
            required=False,
            help="Pass options to vstart. Options should be a list of double quoted strings, "
                 "like '--pass \"mem=64m\" \"eth=0:A\"'."
        )
        parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        parser.add_argument(
            '--print',
            dest="print_only",
            required=False,
            action='store_true',
            help='Print command used to start the containers to stderr (dry run).'
        )
        parser.add_argument(
            '-c', '--counter',
            required=False,
            help='Start from a specific network counter '
                 '(overrides whatever was previously initialized, using 0 will prompt the default behavior).'
        )
        parser.add_argument(
            "--execbash",
            required=False,
            action="store_true",
            help=argparse.SUPPRESS
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lclean_argv = ['-d', args.directory] if args.directory else []

        LcleanCommand().run(lab_path, lclean_argv)
        LstartCommand().run(lab_path, argv)
