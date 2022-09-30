import argparse
import logging
from typing import List

from ..ui.utils import alphanumeric
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...strings import strings, wiki_description


class VconfigCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara vconfig',
            description=strings['vconfig'],
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
            help='Name of the device to be connected on desired collision domains.'
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

        lab = Lab("kathara_vlab")

        machine_name = args['name']
        device = lab.get_or_new_machine(machine_name)
        device.api_object = Kathara.get_instance().get_machine_api_object(machine_name, lab_name=lab.name)

        if args['to_add']:
            for cd in args['to_add']:
                logging.info(
                    "Adding interface to device `%s` on collision domain `%s`..." % (machine_name, cd)
                )
                link = lab.get_or_new_link(cd)
                Kathara.get_instance().connect_machine_to_link(device, link)

        if args['to_remove']:
            for cd in args['to_remove']:
                logging.info(
                    "Removing interface on collision domain `%s` from device `%s`..." % (cd, machine_name)
                )
                (_, link) = lab.connect_machine_to_link(machine_name, cd)
                link.api_object = Kathara.get_instance().get_link_api_object(cd, lab_name=lab.name)

                Kathara.get_instance().disconnect_machine_from_link(device, link)
