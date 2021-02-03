import argparse

from .. import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..strings import strings, wiki_description


class ListCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara list',
            description=strings['list'],
            epilog=wiki_description,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        parser.add_argument(
            '-a', '--all',
            required=False,
            action='store_true',
            help='Show all running Kathara machines of all users. MUST BE ROOT FOR THIS OPTION.'
        )

        parser.add_argument(
            '-r', '--recursive',
            required=False,
            action='store_true',
            help='Show information of multilab'
        )

        parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=False,
            help='Show only information about a specified machine.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        recursive = False
        args = self.parser.parse_args(argv)

        if args.all and not utils.is_admin():
            raise Exception("You must be root in order to show all Kathara devices of all users.")

        if args.name:
            print(ManagerProxy.get_instance().get_machine_info(args.name,all_users=bool(args.all)))
        elif args.recursive:
            recursive = True
            lab_info = ManagerProxy.get_instance().get_lab_info(recursive,all_users=bool(args.all))
            print(next(lab_info))
        else:
            lab_info = ManagerProxy.get_instance().get_lab_info(recursive,all_users=bool(args.all))
            print(next(lab_info))
