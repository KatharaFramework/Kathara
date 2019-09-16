import argparse

import utils
from .Command import Command
from ..deployer.Deployer import Deployer
from ..model.Link import BRIDGE_LINK_NAME
from ..parser.LabParser import LabParser


class LinfoCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara linfo',
            description='Show information about a Kathara lab.'
        )

        parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            '-l', '--live',
            required=False,
            action='store_true',
            help='Live mode, can be used only when a lab is launched.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        if args.live:
            lab_hash = utils.generate_urlsafe_hash(lab_path)

            Deployer.get_instance().get_info_stream(lab_hash)
        else:
            print("========================= Lab Information ==========================")

            lab = LabParser.parse(lab_path)
            lab_meta_information = str(lab)

            if lab_meta_information:
                print(lab_meta_information)
                print("====================================================================")

            n_machines = len(lab.machines)
            n_links = len(lab.links) if BRIDGE_LINK_NAME not in lab.links else len(lab.links) - 1

            print("There are %d machines." % n_machines)
            print("There are %d links." % n_links)

            print("====================================================================")
