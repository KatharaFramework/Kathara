import argparse
import logging
import sys

from .. import utils
from .. import version
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..model.Lab import Lab
from ..setting.Setting import Setting
from ..strings import strings, wiki_description


class CheckCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)
        
        parser = argparse.ArgumentParser(
            prog='kathara check',
            description=strings['check'],
            epilog=wiki_description,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parser.parse_args(argv)

        print("*\tCurrent Manager is: %s" % ManagerProxy.get_instance().get_formatted_manager_name())

        print("*\tManager version is: %s" % ManagerProxy.get_instance().get_release_version())

        print("*\tPython version is: %s" % sys.version.replace("\n", "- "))

        print("*\tKathara version is: %s" % version.CURRENT_VERSION)

        print("*\tTrying to run `Hello World` container...")

        Setting.get_instance().open_terminals = False
        Setting.get_instance().shared_mount = False

        vlab_dir = utils.get_vlab_temp_path()
        lab = Lab(vlab_dir)
        lab.get_or_new_machine("hello_world")

        try:
            ManagerProxy.get_instance().deploy_lab(lab)
            print("*\tContainer run successfully.")
            ManagerProxy.get_instance().undeploy_lab(lab.folder_hash)
        except Exception as e:
            logging.exception("\t! Running `Hello World` failed: %s" % str(e))
