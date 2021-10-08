from typing import Optional, Tuple

MAX_INTERFACE_NAME_LENGTH = 15


class ExternalLink(object):
    """A Kathara external collision domain. It is used to create a collision domain attached to a host interface."""

    __slots__ = ['interface', 'vlan']

    def __init__(self, interface: str, vlan: Optional[int] = None) -> None:
        self.interface: str = interface
        self.vlan: int = vlan

    def get_name_and_vlan(self) -> Tuple[str, Optional[int]]:
        """Return a tuple composed by the name of the attached interface and, if present, the vlan tag.

        The interface name is computed appending the interface name to the vlan tag (if present).
        If the length of interface name + vlan tag is more than 15 chars, the interface name is truncated in order
        to fit the whole string in 15 chars (due to Linux limitations).

        Returns:
            Tuple[str, Optional[int]]: A tuple composed by the name of the attached interface and the vlan tag.
        """
        # VLAN is defined
        if self.vlan:
            vlan_name_length = len(".%s" % self.vlan)

            # If the length of interface name + vlan tag is more than 15 chars, we truncate the interface name to
            # 15 - VLAN_NAME_LENGTH in order to fit the whole string in 15 chars
            return (self.interface, self.vlan) if len(self.interface) + vlan_name_length <= MAX_INTERFACE_NAME_LENGTH \
                else (self.interface[0:(MAX_INTERFACE_NAME_LENGTH - vlan_name_length)], self.vlan)

        return self.interface, None

    def get_full_name(self) -> str:
        """Return the external collision domain full name in the format: |name|.|vlan_tag|.

        Returns:
            (str): The external collision domain full name
        """
        (name, vlan) = self.get_name_and_vlan()
        return name if not vlan else "%s.%s" % (name, vlan)

    def __repr__(self) -> str:
        return "ExternalLink(%s, %s)" % (self.interface, self.vlan)
