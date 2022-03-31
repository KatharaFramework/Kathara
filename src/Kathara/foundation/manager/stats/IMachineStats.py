from abc import ABC, abstractmethod
from typing import Any, Dict


class IMachineStats(ABC):
    @abstractmethod
    def update(self) -> None:
        raise NotImplementedError("You must implement `update` method.")

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("You must implement `to_dict` method.")
