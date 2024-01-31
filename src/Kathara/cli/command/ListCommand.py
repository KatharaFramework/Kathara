import argparse
from typing import List, Optional

from rich.live import Live

from ..ui.utils import create_table
from ... import utils
from ...exceptions import PrivilegeError
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...strings import strings, wiki_description


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
            help='Show a help message and exit.'
        )

        self.parser.add_argument(
            '-a', '--all',
            required=False,
            action='store_true',
            help='Show all running Kathara devices of all users. MUST BE ROOT FOR THIS OPTION.'
        )

        self.parser.add_argument(
            '-w', '-l', '--watch', '--live',
            required=False,
            action='store_true',
            help='Watch mode.'
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
            raise PrivilegeError("You must be root in order to show all Kathara devices of all users.")

        all_users = bool(args['all'])

        if args['watch']:
            self._get_live_info(machine_name=args['name'], all_users=all_users)
        else:
            with self.console.status(
                    f"Loading...",
                    spinner="dots"
            ) as _:
                machines_stats = Kathara.get_instance().get_machines_stats(
                    machine_name=args['name'], all_users=all_users
                )
                self.console.print(create_table(machines_stats))

    def _get_live_info(self, machine_name: Optional[str], all_users: bool) -> None:
        machines_stats = Kathara.get_instance().get_machines_stats(machine_name=machine_name, all_users=all_users)
        with Live(None, refresh_per_second=12.5, screen=True) as live:
            live.update(self.console.status(f"Loading...", spinner="dots"))
            live.refresh_per_second = 1
            while True:
                table = create_table(machines_stats)
                if not table:
                    break

                live.update(table)
