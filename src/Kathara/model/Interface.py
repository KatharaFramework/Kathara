import re
from typing import Optional

from . import Link as LinkPackage
from . import Machine as MachinePackage
from ..exceptions import InterfaceMacAddressError

MAC_ADDRESS_REGEX = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


class Interface(object):
    """Interface object associated to a Machine network interface.

    Attributes:
        machine (Kathara.model.Machine.Machine): The machine associated to this interface.
        link (Kathara.model.Link.Link): The collision domain associated to this interface.
        num (int): The interface number.
        mac_address (Optional[str]): The MAC address of the interface. If None, a generated MAC address
            is associated when the Machine is started.
    """
    __slots__ = ['machine', 'link', 'num', 'mac_address']

    def __init__(self, machine: 'MachinePackage.Machine', link: 'LinkPackage.Link',
                 num: int, mac_address: Optional[str] = None) -> None:
        self.machine: 'MachinePackage.Machine' = machine
        self.link: 'LinkPackage.Link' = link
        self.num: int = num
        self.mac_address: Optional[str] = mac_address

        if self.mac_address and not MAC_ADDRESS_REGEX.match(self.mac_address):
            raise InterfaceMacAddressError(self.mac_address, self.num, machine.name)

    def __repr__(self) -> str:
        return "Interface(%s, %d, %s)" % (self.machine.name, self.num, self.mac_address)
