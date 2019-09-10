import argparse

from classes.commands.Command import Command
from classes.parser.LabParser import LabParser
from classes.deployer.Deployer import Deployer
import utils


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
            help='Specify the folder contining the lab.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        # TODO ma su netkit non si poteva fare "lstart pc1" e startava solo pc1 del lab?
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path

        # Call the parser
        #lab = LabParser.get_instance().lab_parse(lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        Deployer.get_instance().undeploy(lab_hash)