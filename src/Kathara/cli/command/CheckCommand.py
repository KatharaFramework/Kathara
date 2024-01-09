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
            help='Show a help message and exit.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)

        print(f"*\tCurrent Manager is: {Kathara.get_instance().get_formatted_manager_name()}")
        print(f"*\tManager version is: {Kathara.get_instance().get_release_version()}")
        print("*\tPython version is: %s" % sys.version.replace("\n", "- "))
        print(f"*\tKathara version is: {version.CURRENT_VERSION}")

        def linux_platform_info():
            info = os.uname()
            return "%s-%s-%s" % (info.sysname, info.release, info.machine)

        platform_info = utils.exec_by_platform(
            linux_platform_info, lambda: platform.platform(), lambda: platform.platform()
        )
        print(f"*\tOperating System version is: {str(platform_info)}")

        print(f"*\tTrying to run container with `{Setting.get_instance().image}` image...")
        Setting.get_instance().open_terminals = False

        lab = Lab("kathara_test")
        lab.add_option('hosthome_mount', False)

        machine = lab.get_or_new_machine("hello_world")
        try:
            Kathara.get_instance().deploy_machine(machine)
            print("*\tContainer run successfully.")
            Kathara.get_instance().undeploy_machine(machine)
        except Exception as e:
            logging.exception(f"\t! Running container failed: {str(e)}")
