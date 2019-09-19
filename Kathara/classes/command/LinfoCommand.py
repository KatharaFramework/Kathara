import argparse
import os
import time

import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..model.Link import BRIDGE_LINK_NAME
from ..parser.netkit.LabParser import LabParser


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
            self._get_live_info(lab_path)
        else:
            self._get_conf_info(lab_path)

    @staticmethod
    def _get_live_info(lab_path):
        lab_hash = utils.generate_urlsafe_hash(lab_path)

        lab_info = ManagerProxy.get_instance().get_lab_info(lab_hash)

        while True:
            utils.exec_by_platform(lambda: os.system('clear'), lambda: os.system('cls'), lambda: os.system('clear'))
            print(next(lab_info))
            time.sleep(1)

    @staticmethod
    def _get_conf_info(lab_path):
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
