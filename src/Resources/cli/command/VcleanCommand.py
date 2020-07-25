import argparse
import logging

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.ManagerProxy import ManagerProxy
from ...strings import strings, wiki_description


class VcleanCommand(Command):
    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vclean',
            description=strings['vclean'],
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
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the machine to be cleaned.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parse_args(argv)
        args = self.get_args()

        vlab_dir = utils.get_vlab_temp_path()
        lab_hash = utils.generate_urlsafe_hash(vlab_dir)

        ManagerProxy.get_instance().undeploy_lab(lab_hash,
                                                 selected_machines={args.name}
                                                 )

        logging.info("Machine `%s` deleted successfully!" % args.name)
