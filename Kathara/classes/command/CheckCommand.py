import argparse
import sys

from ..controller.Controller import Controller
from ..foundation.command.Command import Command
from ..model.Lab import Lab
from ..setting.Setting import KATHARA_VERSION


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

        print("*\tController version is: %s" % Controller.get_instance().get_version())

        print("*\tTrying to run `Hello World` container...")
        lab = Lab("/tmp")
        machine = lab.get_or_new_machine("hello_world")
        machine.add_meta("image", "hello-world")
        Controller.get_instance().deploy_lab(lab)
        Controller.get_instance().undeploy_lab(lab)

        print("*\tPython version is: %s" % sys.version.replace("\n", "- "))

        print("*\tKathara version is: %s" % KATHARA_VERSION)
