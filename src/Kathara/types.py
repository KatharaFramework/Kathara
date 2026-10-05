from enum import Enum, IntEnum


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
    def to_string(value):
        if value == 1:
            return "Not Shared"
        elif value == 2:
            return "Share collision domains between network scenarios"
        elif value == 3:
            return "Share collision domains between users"


class LinkMode(str, Enum):
    """Enum representing the behaviour of a collision domain.

    Attributes:
        HUB (str): Each frame is sent to all the devices of the collision domain (value: "hub").
        SWITCH (str): The collision domain learns the MAC addresses and sends a frame only to its destination,
            without any configuration (value: "switch").
        MANAGED (str): A switch which can be configured: VLANs declared on the interfaces of the devices and
            commands sent at runtime (value: "managed").
    """
    HUB = "hub"
    SWITCH = "switch"
    MANAGED = "managed"
