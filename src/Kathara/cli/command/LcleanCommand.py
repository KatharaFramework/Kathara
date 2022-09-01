import argparse
import logging
from typing import List

from ..ui.utils import format_headers
from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description


class LcleanCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara lclean',
            description=strings['lclean'],
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
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the network scenario.'
        )
        self.parser.add_argument(
            'machine_names',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Clean only specified devices.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)
        try:
            lab = LabParser.parse(lab_path)
        except (Exception, IOError):
            lab = Lab(None, path=lab_path)

        logging.info(format_headers("Stopping Network Scenario"))

        Kathara.get_instance().undeploy_lab(lab_hash=lab.hash, selected_machines=set(args['machine_names']))
