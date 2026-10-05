import argparse
from typing import List

from ..ui.utils import create_lab_table
from ..ui.utils import create_panel
from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...setting.Setting import Setting
from ...strings import strings, wiki_description


class RestoreCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara restore',
            description=strings['restore'],
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
            default=None,
            help='Restore the network scenario without opening terminal windows.'
        )
        group.add_argument(
            "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Restore the network scenario opening terminal windows.'
        )
        self.parser.add_argument(
            '-l', '--list',
            required=False,
            action='store_true',
            help='Show information about restored devices after the network scenario has been restored.'
        )
        self.parser.add_argument(
            'archive',
            metavar='SAVE_FILE',
            help='Path of the save file to restore (created by `kathara save`).'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        archive_path = args['archive'].replace('"', '').replace("'", '')
        archive_path = utils.get_absolute_path(archive_path)

        Setting.get_instance().open_terminals = args['terminals'] if args['terminals'] is not None \
            else Setting.get_instance().open_terminals

        self.console.print(create_panel("Restoring Network Scenario", style="blue bold", justify="center"))

        lab = Kathara.get_instance().restore_lab(archive_path)

        if args['list']:
            with self.console.status("Loading...", spinner="dots") as _:
                machines_stats = Kathara.get_instance().get_machines_stats(lab_hash=lab.hash)
                self.console.print(create_lab_table(machines_stats))

        return 0
