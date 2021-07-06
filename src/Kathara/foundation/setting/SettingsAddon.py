from abc import ABC, abstractmethod


class SettingsAddon(ABC):
    def load(self, settings):
        for name, value in settings.items():
            if hasattr(self, name):
                setattr(self, name, value)

    def get(self, name):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            raise AttributeError

    def merge(self, settings=None):
        to_dict = self._to_dict()

        if settings:
            settings.update(to_dict)
            return settings

        return to_dict

    @abstractmethod
    def _to_dict(self):
        pass
