import argparse
import logging
import sys
import tempfile

from .. import version
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..model.Lab import Lab
from ..setting.Setting import Setting


class CheckCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)
        
        parser = argparse.ArgumentParser(
            prog='kathara check',
            description='Check your system environment.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parser.parse_args(argv)

        print("*\tManager version is: %s" % ManagerProxy.get_instance().get_release_version())

        print("*\tTrying to run `Hello World` container...")
        lab = Lab(tempfile.gettempdir())
        lab.shared_folder = None
        machine = lab.get_or_new_machine("hello_world")
        machine.add_meta("image", Setting.get_instance().image)
        try:
            ManagerProxy.get_instance().deploy_lab(lab)
            print("*\tContainer run successfully.")
            ManagerProxy.get_instance().undeploy_lab(lab.folder_hash)
        except Exception as e:
            logging.exception("\t! Running `Hello World` failed: %s" % str(e))

        print("*\tPython version is: %s" % sys.version.replace("\n", "- "))

        print("*\tKathara version is: %s" % version.CURRENT_VERSION)
