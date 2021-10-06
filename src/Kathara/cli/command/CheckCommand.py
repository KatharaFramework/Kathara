import argparse
import logging
import os
import platform
import sys
from typing import List

from ... import utils
from ... import version
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...setting.Setting import Setting
from ...strings import strings, wiki_description


class CheckCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara check',
            description=strings['check'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        print("*\tCurrent Manager is: %s" % Kathara.get_instance().get_formatted_manager_name())

        print("*\tManager version is: %s" % Kathara.get_instance().get_release_version())

        print("*\tPython version is: %s" % sys.version.replace("\n", "- "))

        print("*\tKathara version is: %s" % version.CURRENT_VERSION)

        def linux_platform_info():
            info = os.uname()
            return "%s-%s-%s" % (info.sysname, info.release, info.machine)

        platform_info = utils.exec_by_platform(
            linux_platform_info, lambda: platform.platform(), lambda: platform.platform()
        )
        print("*\tOperating System version is: %s" % str(platform_info))

        print("*\tTrying to run `Hello World` container...")

        Setting.get_instance().open_terminals = False
        args['no_shared'] = False
        args['no_hosthome'] = False

        lab = Lab("kathara_vlab")
        lab.get_or_new_machine("hello_world")

        try:
            Kathara.get_instance().deploy_lab(lab)
            print("*\tContainer run successfully.")
            Kathara.get_instance().undeploy_lab(lab.hash)
        except Exception as e:
            logging.exception("\t! Running `Hello World` failed: %s" % str(e))
