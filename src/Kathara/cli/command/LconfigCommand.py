import argparse
import logging
import re
import sys
from typing import List

from ... import utils
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
            help='Show an help message and exit.'
        )
        self.parser.add_argument(
            '-d', '--directory',
            metavar='LAB_PATH',
            required=False,
            help='Path of the lab to configure, if not specified the current path is used'
        )
        self.parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the device to be connected on desired collision domains.'
        )
        self.parser.add_argument(
            '--eth',
            dest='eths',
            metavar='CD',
            nargs='+',
            required=True,
            help='Specify the collision domain for an interface.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        for eth in args['eths']:
            # Only alphanumeric characters are allowed
            matches = re.search(r"^\w+$", eth)

            if not matches:
                sys.stderr.write('Syntax error in --eth field.\n')
                self.parser.print_help()
                exit(1)

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)
        try:
            lab = LabParser.parse(lab_path)
        except (Exception, IOError):
            lab = Lab(None, path=lab_path)

        machine_name = args['name']
        device = lab.get_or_new_machine(machine_name)
        device.api_object = Kathara.get_instance().get_machine_api_object(machine_name, lab_hash=lab.hash)

        for eth in args['eths']:
            logging.info("Adding interface to device `%s` for collision domain `%s`..." % (machine_name, eth))
            lab.connect_machine_to_link(machine_name, eth)

        # Remove all the lab machines, except the one to update
        lab.machines = {machine_name: device}

        Kathara.get_instance().update_lab(lab)
