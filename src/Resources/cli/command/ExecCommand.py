import argparse
import sys

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.ManagerProxy import ManagerProxy
from ...strings import strings, wiki_description


class ExecCommand(Command):
    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara exec',
            description=strings['exec'],
            epilog=wiki_description,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        group = parser.add_mutually_exclusive_group(required=False)

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
        parser.add_argument(
            '--no-stdout',
            dest="no_stdout",
            action="store_true",
            help='Disable stdout of the executed command.',
        )
        parser.add_argument(
            '--no-stderr',
            dest="no_stderr",
            action="store_true",
            help='Disable stderr of the executed command.',
        )
        parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            help='Name of the device to execute the command into.'
        )
        parser.add_argument(
            'command',
            metavar='COMMAND',
            nargs='+',
            help='Shell command that will be executed inside the device.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parse_args(argv)
        args = self.get_args()

        if args.vmachine:
            lab_path = utils.get_vlab_temp_path()
        else:
            lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
            lab_path = utils.get_absolute_path(lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        (stdout, stderr) = ManagerProxy.get_instance().exec(lab_hash, args.machine_name, args.command)

        if not args.no_stdout:
            sys.stdout.write(stdout)

        if stderr and not args.no_stderr:
            sys.stderr.write(stderr)
