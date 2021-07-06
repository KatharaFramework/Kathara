from ..ui.setting.SettingsMenuFactory import SettingsMenuFactory
from ...foundation.cli.command.Command import Command


class SettingsCommand(Command):
    def run(self, current_path, argv):
        menu_factory = SettingsMenuFactory()

        menu = menu_factory.create_menu()

        menu.show()
