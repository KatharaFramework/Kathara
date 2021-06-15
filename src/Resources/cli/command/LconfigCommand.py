import argparse
import logging
import re
import sys

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.ManagerProxy import ManagerProxy
from ...model.Lab import Lab
from ...strings import strings, wiki_description


class LconfigCommand(Command):
    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lconfig',
            description=strings['lconfig'],
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
            '-d', '--directory',
            metavar='LAB_PATH',
            required=False,
            help='Path of the lab to configure, if not specified the current path is used'
        )
        parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the device to be connected on desired collision domains.'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            metavar='CD',
            nargs='+',
            required=True,
            help='Specify the collision domain for an interface.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)

        for eth in args.eths:
            # Only alphanumeric characters are allowed
            matches = re.search(r"^\w+$", eth)

            if not matches:
                sys.stderr.write('Syntax error in --eth field.\n')
                self.parser.print_help()
                exit(1)

        lab = Lab(None, path=lab_path)

        iface_number = 0
        for eth in args['eths']:
            logging.info("Adding interface to device `%s` for collision domain `%s`..." % (args['name'], eth))

            lab.connect_machine_to_link(args['name'], iface_number, eth)
            iface_number += 1

        ManagerProxy.get_instance().update_lab(lab)
