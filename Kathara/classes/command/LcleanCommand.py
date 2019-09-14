import argparse

import utils
from .Command import Command
from ..deployer.Deployer import Deployer


class LcleanCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lclean',
            description='Stops a Kathara Lab.'
        )

        parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        Deployer.get_instance().undeploy_lab(lab_hash)
