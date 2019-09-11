import argparse

from classes.command.Command import Command
from classes.deployer.Deployer import Deployer
from classes.setting.Setting import Setting


class WipeCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara wipe',
            description='Delete all Kathara machines and links.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parser.parse_args(argv)

        Deployer.get_instance().wipe()

        setting_object = Setting.get_instance()
        setting_object.net_counter = 0
        setting_object.save_selected(['net_counter'])
