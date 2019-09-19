import argparse

import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy


class ConnectCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)
        
        parser = argparse.ArgumentParser(
            prog='kathara connect',
            description='Connect to a Kathara machine.'
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
            help='Set the shell (sh, bash, etc.) that should be used inside the machine.'
        )
        parser.add_argument(
            'machine_name',
            help='Name of the machine to connect to'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        if args.vmachine:
            lab_path = utils.get_vlab_temp_path()
        else:
            lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
            lab_path = utils.get_absolute_path(lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        ManagerProxy.get_instance().connect_tty(lab_hash,
                                                machine_name=args.machine_name,
                                                shell=args.shell
                                                )
