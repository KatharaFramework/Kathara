import argparse
from typing import List

from ..ui.utils import create_panel
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...strings import strings, wiki_description


class VcleanCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara vclean',
            description=strings['vclean'],
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
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='The name of the device to clean.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        lab = Lab("kathara_vlab")

        self.console.print(
            create_panel(f"Stopping Device `{args['name']}`", style="blue bold", justify="center")
        )

        Kathara.get_instance().undeploy_lab(lab_name=lab.name, selected_machines={args['name']})
