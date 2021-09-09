import argparse
from typing import List

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...strings import strings, wiki_description
from ...trdparty.curses.curses import Curses


class ListCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara list',
            description=strings['list'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        self.parser.add_argument(
            '-a', '--all',
            required=False,
            action='store_true',
            help='Show all running Kathara devices of all users. MUST BE ROOT FOR THIS OPTION.'
        )

        self.parser.add_argument(
            '-l', '--live',
            required=False,
            action='store_true',
            help='Live mode.'
        )

        self.parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=False,
            help='Show only information about a specified device.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        if args['all'] and not utils.is_admin():
            raise Exception("You must be root in order to show all Kathara devices of all users.")

        all_users = bool(args['all'])

        if args['live']:
            if args['name']:
                self._get_machine_live_info(args['name'], all_users)
            else:
                self._get_lab_live_info(all_users)
        else:
            if args['name']:
                print(Kathara.get_instance().get_formatted_machine_info(args['name'], all_users=all_users))
            else:
                lab_info = Kathara.get_instance().get_formatted_lab_info(all_users=all_users)

                print(next(lab_info))

    @staticmethod
    def _get_machine_live_info(machine_name: str, all_users: bool) -> None:
        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(
                    Kathara.get_instance().get_formatted_machine_info(machine_name, all_users=all_users)
                )
        finally:
            Curses.get_instance().close()

    @staticmethod
    def _get_lab_live_info(all_users: bool) -> None:
        lab_info = Kathara.get_instance().get_formatted_lab_info(all_users=all_users)

        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(next(lab_info))
        except StopIteration:
            pass
        finally:
            Curses.get_instance().close()
