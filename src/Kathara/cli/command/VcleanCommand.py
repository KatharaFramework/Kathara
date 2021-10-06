import argparse
import logging
from typing import List

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
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
            help='Show an help message and exit.'
        )

        self.parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the device to be cleaned.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        lab_hash = utils.generate_urlsafe_hash("kathara_vlab")

        Kathara.get_instance().undeploy_lab(lab_hash,
                                            selected_machines={args['name']}
                                            )

        logging.info("Device `%s` deleted successfully!" % args['name'])
