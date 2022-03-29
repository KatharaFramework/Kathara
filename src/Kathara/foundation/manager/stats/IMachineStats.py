from abc import ABC, abstractmethod
from typing import Any


class IMachineStats(ABC):

    @abstractmethod
    def __init__(self, machine_api_object: Any):
        raise NotImplementedError("You must implement `init` method.")

    @abstractmethod
    def update(self) -> None:
        raise NotImplementedError("You must implement `update` method.")
