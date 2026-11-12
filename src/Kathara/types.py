from enum import IntEnum, StrEnum
from typing import Optional


class SharedCollisionDomainsOption(IntEnum):
    """Enum representing options for shared collision domains option.

    Attributes:
        NOT_SHARED (int): Represents the option for not sharing collision domains (value: 1).
        LABS (int): Represents the option for sharing collision domains among network scenarios of the same user
            (value: 2).
        USERS (int): Represents the option for sharing collision domains among network scenarios of different users
            (value: 3).
    """
    NOT_SHARED = 1
    LABS = 2
    USERS = 3

    @staticmethod
    def to_string(value) -> Optional[str]:
        if value == 1:
            return "Not Shared"
        elif value == 2:
            return "Share collision domains between network scenarios"
        elif value == 3:
            return "Share collision domains between users"
        else:
            return None


class CollisionDomainTypesOption(StrEnum):
    """Enum representing options for collision domains types.

    Attributes:
        BRIDGE (str): Bridge type, uses Linux bridges.
        HUB (str): Hub type, uses VDE switches.
        P2P (str): P2P type, uses veth pairs.
    """
    BRIDGE = "bridge"
    HUB = "hub"
    P2P = "p2p"

    @classmethod
    def parse(cls, value: str) -> 'CollisionDomainTypesOption':
        """Convert a string to a collision domain type.

        Args:
            value (str): The collision domain type, as a string.

        Returns:
            CollisionDomainTypesOption: The corresponding collision domain type.

        Raises:
            ValueError: If the value is not a supported collision domain type.
        """
        try:
            return cls(value)
        except ValueError:
            supported = ", ".join(f"`{x.value}`" for x in cls)
            raise ValueError(f"Invalid collision domain type `{value}`. Supported types are {supported}.") from None
