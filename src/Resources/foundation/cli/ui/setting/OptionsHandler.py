from abc import ABC, abstractmethod


class OptionsHandler(ABC):
    __slots__ = ['menu_factory']

    def __init__(self):
        self.menu_factory = None

    def add(self, current_menu, menu_formatter):
        if not self.menu_factory:
            raise Exception("`add` called without a MenuFactory set.")

        self.add_items(current_menu, menu_formatter)

    @abstractmethod
    def add_items(self, current_menu, menu_formatter):
        raise NotImplementedError("You must implement `add_items` method.")

    def set_menu_factory(self, menu_factory):
        self.menu_factory = menu_factory
