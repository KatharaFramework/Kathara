import argparse

import utils
from classes.command.Command import Command
from classes.deployer.Deployer import Deployer


class LcleanCommand(Command):
    __slots__ = []

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
        # TODO ma su netkit non si poteva fare "lclean pc1" e stoppava solo pc1 del lab?
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_hash = utils.generate_urlsafe_hash(lab_path)

        Deployer.get_instance().undeploy_lab(lab_hash)
