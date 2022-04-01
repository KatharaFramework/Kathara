from abc import ABC, abstractmethod
from typing import Dict, Any


class ILinkStats(ABC):
    """Interface for handling the statistics of deployed collision domains"""

    @abstractmethod
    def update(self) -> None:
        """Update dynamic statistics with the current ones.

        Returns:
            None
        """
        raise NotImplementedError("You must implement `update` method.")

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("You must implement `to_dict` method.")
