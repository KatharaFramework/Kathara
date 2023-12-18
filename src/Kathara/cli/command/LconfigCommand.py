import argparse
import logging
from typing import List

from ... import utils
from ..ui.utils import alphanumeric
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description


class LconfigCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara lconfig',
            description=strings['lconfig'],
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
            '-d', '--directory',
            metavar='LAB_PATH',
            required=False,
            help='Path of the network scenario to configure, if not specified the current path is used'
        )
        self.parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the device to configure.'
        )

        group = self.parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            '--add',
            type=alphanumeric,
            dest='to_add',
            metavar='CD',
            nargs='+',
            help='Specify the collision domain to add.'
        )
        group.add_argument(
            '--rm',
            type=alphanumeric,
            dest='to_remove',
            metavar='CD',
            nargs='+',
            help='Specify the collision domain to remove.'
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

        Kathara.get_instance().update_lab_from_api(lab)

        machine_name = args['name']
        device = lab.get_machine(machine_name)

        if args['to_add']:
            for cd in args['to_add']:
                logging.info(
                    "Adding interface to device `%s` on collision domain `%s`..." % (machine_name, cd)
                )
                Kathara.get_instance().connect_machine_to_link(device, lab.get_or_new_link(cd))

        if args['to_remove']:
            for cd in args['to_remove']:
                logging.info(
                    "Removing interface on collision domain `%s` from device `%s`..." % (cd, machine_name)
                )
                Kathara.get_instance().disconnect_machine_from_link(device, lab.get_or_new_link(cd))
