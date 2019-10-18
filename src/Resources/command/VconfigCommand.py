import argparse
import logging
import re
import sys

from .. import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..model.Lab import Lab
from ..strings import strings, wiki_description


class VconfigCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vconfig',
            description=strings['vconfig'],
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
            '-n', '--name',
            metavar='MACHINE_NAME',
            required=True,
            help='Name of the machine to be connected on desired collision domains.'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            metavar='N:CD',
            nargs='+',
            required=True,
            help='Specify the collision domain for an interface.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        for eth in args.eths:
            # Only alphanumeric characters are allowed
            matches = re.search(r"^\w+$", eth)

            if not matches:
                sys.stderr.write('Syntax error in --eth field.\n')
                self.parser.print_help()
                exit(1)

        vlab_dir = utils.get_vlab_temp_path()
        lab = Lab(vlab_dir)

        iface_number = 0
        for eth in args.eths:
            logging.info("Adding interface to machine `%s` for collision domain `%s`..." % (args.name, eth))

            lab.connect_machine_to_link(args.name, iface_number, eth)
            iface_number += 1

        ManagerProxy.get_instance().update_lab(lab)
