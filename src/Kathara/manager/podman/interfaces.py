import re
from typing import Optional

# Network alias used to persist the number of a Kathará interface. Labels cannot be updated on a
# running container, but a network alias can be set both at container creation and at `connect()`
# time, and is returned by inspect in `NetworkSettings.Networks[<network>].Aliases`.
# Lives in its own module so that both PodmanMachine and PodmanMachineStats can import it
# without a circular import.
IFACE_ALIAS_PREFIX = "kathara-eth"
IFACE_ALIAS_RE = re.compile(rf"^{re.escape(IFACE_ALIAS_PREFIX)}(\d+)$")


def build_iface_alias(interface_num: int) -> str:
    """Return the network alias used to persist the number of a Kathará interface.

    Args:
        interface_num (int): The number of the interface (e.g. `1` for `eth1`).

    Returns:
        str: The alias, e.g. `kathara-eth1`.
    """
    return f"{IFACE_ALIAS_PREFIX}{interface_num}"


def parse_iface_alias(alias: str) -> Optional[int]:
    """Parse the interface number out of a `kathara-eth<N>` network alias.

    Args:
        alias (str): A network alias.

    Returns:
        Optional[int]: The interface number, or None if `alias` is not a Kathará interface alias.
    """
    match = IFACE_ALIAS_RE.match(alias)
    return int(match.group(1)) if match else None
