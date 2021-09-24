from .CommonOptionsHandler import CommonOptionsHandler
from ....foundation.cli.ui.setting.OptionsHandlerFactory import OptionsHandlerFactory
from ....setting.Setting import Setting
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.format import MenuBorderStyleType


class SettingsMenuFactory(object):
    __slots__ = ['menu_formatter']

    def __init__(self) -> None:
        self.menu_formatter: MenuFormatBuilder = MenuFormatBuilder().set_title_align('center') \
            .set_subtitle_align('center') \
            .set_prologue_text_align('center') \
            .set_border_style_type(MenuBorderStyleType.DOUBLE_LINE_BORDER) \
            .show_prologue_top_border(True) \
            .show_prologue_bottom_border(True)

    def create_menu(self) -> ConsoleMenu:
        menu = ConsoleMenu(title="Kathara Settings",
                           prologue_text="Choose the option to change.",
                           formatter=self.menu_formatter
                           )

        common_settings = CommonOptionsHandler()
        common_settings.set_menu_factory(self)
        common_settings.add(menu, self.menu_formatter)

        manager_type = Setting.get_instance().manager_type
        manager_settings = OptionsHandlerFactory().create_instance(class_args=(manager_type.capitalize(),))
        manager_settings.set_menu_factory(self)
        manager_settings.add(menu, self.menu_formatter)

        return menu
