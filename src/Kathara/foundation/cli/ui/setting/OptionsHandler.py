from abc import ABC, abstractmethod
from typing import Optional

from .....cli.ui.setting import SettingsMenuFactory
from .....trdparty.consolemenu import ConsoleMenu, MenuFormatBuilder


class OptionsHandler(ABC):
    __slots__ = ['menu_factory']

    def __init__(self) -> None:
        self.menu_factory: Optional['SettingsMenuFactory.SettingsMenuFactory'] = None

    def add(self, current_menu: ConsoleMenu, menu_formatter: MenuFormatBuilder) -> None:
        if not self.menu_factory:
            raise Exception("`add` called without a MenuFactory set.")

        self.add_items(current_menu, menu_formatter)

    @abstractmethod
    def add_items(self, current_menu: ConsoleMenu, menu_formatter: MenuFormatBuilder) -> None:
        raise NotImplementedError("You must implement `add_items` method.")

    def set_menu_factory(self, menu_factory: 'SettingsMenuFactory.SettingsMenuFactory') -> None:
        self.menu_factory = menu_factory
