import argparse
import sys
from typing import List

import chardet

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description


class ExecCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara exec',
            description=strings['exec'],
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
            help='The device has been started with vstart command.',
        )
        self.parser.add_argument(
            '--no-stdout',
            dest="no_stdout",
            action="store_true",
            help='Disable stdout of the executed command.',
        )
        self.parser.add_argument(
            '--no-stderr',
            dest="no_stderr",
            action="store_true",
            help='Disable stderr of the executed command.',
        )
        self.parser.add_argument(
            '--wait',
            dest="wait",
            action="store_true",
            default=False,
            help='Wait until startup commands execution finishes.',
        )
        self.parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            help='Name of the device to execute the command into.'
        )
        self.parser.add_argument(
            'command',
            metavar='COMMAND',
            nargs='+',
            help='Shell command that will be executed inside the device.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        if args['vmachine']:
            lab = Lab("kathara_vlab")
        else:
            lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
            lab_path = utils.get_absolute_path(lab_path)
            try:
                lab = LabParser.parse(lab_path)
            except (Exception, IOError):
                lab = Lab(None, path=lab_path)

        exec_output = Kathara.get_instance().exec(
            args['machine_name'],
            args['command'] if len(args['command']) > 1 else args['command'].pop(),
            lab_hash=lab.hash,
            wait=args['wait']
        )

        try:
            while True:
                (stdout, stderr) = next(exec_output)

                if not args['no_stdout']:
                    stdout_char_encoding = chardet.detect(stdout) if stdout else None
                    stdout = stdout.decode(stdout_char_encoding['encoding']) if stdout else ""
                    sys.stdout.write(stdout)
                if stderr and not args['no_stderr']:
                    stderr_char_encoding = chardet.detect(stderr) if stderr else None
                    stderr = stderr.decode(stderr_char_encoding['encoding']) if stderr else ""
                    sys.stderr.write(stderr)
        except StopIteration:
            pass

        return exec_output.exit_code()
