import argparse

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.ManagerProxy import ManagerProxy
from ...strings import strings, wiki_description


class ConnectCommand(Command):
    def __init__(self):
        Command.__init__(self)
        
        parser = argparse.ArgumentParser(
            prog='kathara connect',
            description=strings['connect'],
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
            help='The machine has been started with vstart command.',
        )
        parser.add_argument(
            '--shell',
            required=False,
            help='Shell that should be used inside the machine.'
        )
        parser.add_argument(
            '-l', '--logs',
            action="store_true",
            help='Print machine startup logs before launching the shell.',
        )
        parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            help='Name of the machine to connect to.'
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

        ManagerProxy.get_instance().connect_tty(lab_hash, machine_name=args.machine_name, shell=args.shell,
                                                logs=args.logs)
