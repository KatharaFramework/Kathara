from abc import ABC, abstractmethod
from typing import Dict, Any


class SettingsAddon(ABC):
    def load(self, settings: Dict[str, Any]) -> None:
        for name, value in settings.items():
            if hasattr(self, name):
                setattr(self, name, value)

    def get(self, name: str) -> Any:
        if hasattr(self, name):
            return getattr(self, name)
        else:
            raise AttributeError

    def merge(self, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        to_dict = self._to_dict()

        if settings:
            settings.update(to_dict)
            return settings

        return to_dict

    @abstractmethod
    def _to_dict(self) -> Dict[str, Any]:
        pass
