import argparse
import shutil

import utils
from ..proxy.ManagerProxy import ManagerProxy
from ..foundation.command.Command import Command
from ..setting.Setting import Setting


class WipeCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara wipe',
            description='Delete all Kathara machines and links.'
        )

        parser.add_argument(
            '-f', '--force',
            required=False,
            action='store_true',
            help='Force the wipe.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        if not args.force:
            answer = None
            while answer not in ["y", "yes", "Y", "YES", "n", "no", "N", "NO"]:
                answer = input("Are you sure to wipe Kathara? [y/n] ")

                if answer in ["n", "no", "NO"]:
                    exit(0)

        ManagerProxy.get_instance().wipe()

        setting_object = Setting.get_instance()
        setting_object.net_counter = 0
        setting_object.save_selected(['net_counter'])

        vlab_dir = utils.get_vlab_temp_path(force_creation=False)
        shutil.rmtree(vlab_dir, ignore_errors=True)
