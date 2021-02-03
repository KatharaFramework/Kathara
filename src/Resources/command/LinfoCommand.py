import argparse
import os
import time

from .. import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..model.Link import BRIDGE_LINK_NAME
from ..parser.netkit.LabParser import LabParser
from ..strings import strings, wiki_description


class LinfoCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara linfo',
            description=strings['linfo'],
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
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            '-l', '--live',
            required=False,
            action='store_true',
            help='Live mode, can be used only when a lab is launched.'
        )

        parser.add_argument(
            '-r', '--recursive',
            required=False,
            action='store_true',
            help='Show information of multilab'
        )

        parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=False,
            help='Show only information about a specified machine.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)
        lab_hash = utils.generate_urlsafe_hash(lab_path)

        if args.live:
            recursive = False
            self._get_live_info(recursive,lab_hash, args.name)
        elif args.recursive:
            recursive = True
            self._get_live_info(recursive,lab_hash,args.name)
        else:
            if args.name:
                print(ManagerProxy.get_instance().get_machine_info(args.name, lab_hash))
            else:
                self._get_conf_info(lab_path)

    @staticmethod
    def _get_live_info(lab_hash, machine_name,recursive):
        lab_info = ManagerProxy.get_instance().get_lab_info(recursive,lab_hash, machine_name)

        while True:
            utils.exec_by_platform(lambda: os.system('clear'), lambda: os.system('cls'), lambda: os.system('clear'))
            print(next(lab_info))
            time.sleep(1)

    @staticmethod
    def _get_conf_info(lab_path):
        print(utils.format_headers("Lab Information"))

        lab = LabParser.parse(lab_path)
        lab_meta_information = str(lab)

        if lab_meta_information:
            print(lab_meta_information)
            print("=============================================================")

        n_machines = len(lab.machines)
        n_links = len(lab.links) if BRIDGE_LINK_NAME not in lab.links else len(lab.links) - 1

        print("There are %d machines." % n_machines)
        print("There are %d links." % n_links)

        print("=============================================================")
