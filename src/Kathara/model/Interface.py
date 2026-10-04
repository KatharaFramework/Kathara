import re
from typing import Optional, List

from . import Link as LinkPackage
from . import Machine as MachinePackage
from ..exceptions import InterfaceMacAddressError, InterfaceVlanError

MAC_ADDRESS_REGEX = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")

MIN_VLAN_ID = 1
MAX_VLAN_ID = 4094


class Interface(object):
    """Interface object associated to a Machine network interface.

    Attributes:
        machine (Kathara.model.Machine.Machine): The machine associated to this interface.
        link (Kathara.model.Link.Link): The collision domain associated to this interface.
        num (int): The interface number.
        mac_address (Optional[str]): The MAC address of the interface. If None, a generated MAC address
            is associated when the Machine is started.
        vlan (Optional[int]): The VLAN of the untagged frames of the interface, on a managed collision domain.
            If None, the interface is in the default VLAN of the collision domain.
        tagged_vlans (List[int]): The VLANs whose tagged (802.1Q) frames are exchanged with the interface,
            on a managed collision domain.
    """
    __slots__ = ['machine', 'link', 'num', 'mac_address', 'vlan', 'tagged_vlans']

    def __init__(self, machine: 'MachinePackage.Machine', link: 'LinkPackage.Link',
                 num: int, mac_address: Optional[str] = None, vlan: Optional[int] = None,
                 tagged_vlans: Optional[List[int]] = None) -> None:
        self.machine: 'MachinePackage.Machine' = machine
        self.link: 'LinkPackage.Link' = link
        self.num: int = num
        self.mac_address: Optional[str] = mac_address
        self.vlan: Optional[int] = vlan
        self.tagged_vlans: List[int] = sorted(set(tagged_vlans)) if tagged_vlans else []

        if self.mac_address and not MAC_ADDRESS_REGEX.match(self.mac_address):
            raise InterfaceMacAddressError(self.mac_address, self.num, machine.name)

        for vlan_id in ([self.vlan] if self.vlan is not None else []) + self.tagged_vlans:
            if type(vlan_id) is not int or not MIN_VLAN_ID <= vlan_id <= MAX_VLAN_ID:
                raise InterfaceVlanError(
                    f"VLAN `{vlan_id}` on interface `{self.num}` of device `{machine.name}` is invalid, "
                    f"it must be a number between {MIN_VLAN_ID} and {MAX_VLAN_ID}."
                )

        if self.vlan is not None and self.vlan in self.tagged_vlans:
            raise InterfaceVlanError(
                f"VLAN `{self.vlan}` on interface `{self.num}` of device `{machine.name}` "
                f"cannot be both untagged and tagged."
            )

    def check_vlans(self) -> None:
        """Check that the VLANs of the interface can be applied by its collision domain.

        Returns:
            None

        Raises:
            InterfaceVlanError: If VLANs are set and the collision domain is not a managed switch.
        """
        if self.has_vlans() and not self.link.is_managed():
            raise InterfaceVlanError(
                f"VLANs are set on interface `{self.num}` of device `{self.machine.name}`, "
                f"but collision domain `{self.link.name}` is not a managed switch."
            )

    def has_vlans(self) -> bool:
        """Check if VLANs are set on the interface.

        Returns:
            bool: True if the interface has an untagged VLAN or tagged VLANs.
        """
        return self.vlan is not None or len(self.tagged_vlans) > 0

    def __repr__(self) -> str:
        return "Interface(%s, %d, %s)" % (self.machine.name, self.num, self.mac_address)
