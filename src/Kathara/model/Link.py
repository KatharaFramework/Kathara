from typing import Any, Dict, Optional

from . import Lab as LabPackage
from . import Machine as MachinePackage
from .. import utils
from ..exceptions import LinkInvalidError, LinkOptionError
from ..types import CollisionDomainTypesOption

BRIDGE_LINK_NAME = "kathara_host_bridge"


class Link(object):
    """A Kathara collision domain.

    Contains information about the collision domain and the API object to interact with the Manager.

    Attributes:
        lab (Kathara.model.Lab.Lab): The Kathara network scenario of the collision domain.
        name (str): The name of the collision domain.
        machines (Dict[str, Kathara.model.Machine.Machine]): Machines attached to this collision domain.
        api_object (Any): To interact with the current Kathara Manager.
        meta (Dict[str, Any]): Metadata of the collision domain.
    """
    __slots__ = ['lab', 'name', 'machines', 'api_object', 'meta']

    def __init__(self, lab: 'LabPackage.Lab', name) -> None:
        self.lab: 'LabPackage.Lab' = lab
        self.name: str = name
        self.machines: Dict[str, 'MachinePackage.Machine'] = {}
        self.api_object: Any = None

        self.meta: Dict[str, Any] = {
            'type': None,
            'external': [],
        }

    def update_meta(self, meta: Dict[str, Any]) -> None:
        """Update the meta properties of the collision domain.

        Args:
            meta (Dict[str, Any]): Keys are meta names, values are meta values.

        Returns:
            None

        Raises:
            ValueError: If the type is not a supported collision domain type.
            LinkOptionError: If the value of `ageing_time` or `group_fwd_mask` is not valid.
        """
        for name, value in meta.items():
            self.add_meta(name, value)

    def add_meta(self, name: str, value: Any) -> Optional[Any]:
        """Add a meta property to the collision domain.

        Args:
            name (str): The name of the property.
            value (Any): The value of the property.

        Returns:
            Optional[Any]: The previous value of the property, None if it was not set.

        Raises:
            ValueError: If the type is not a supported collision domain type.
            LinkOptionError: If the value of `ageing_time` or `group_fwd_mask` is not valid.
        """
        old_value = self.meta[name] if name in self.meta else None

        if name == 'type':
            self.meta[name] = CollisionDomainTypesOption.parse(value) if value is not None else None
            return old_value

        if name == 'external':
            old_value = list(old_value)
            self.meta[name] += value
            return old_value

        if name == 'ageing_time':
            try:
                # Limit accepted by the Linux bridge (IFLA_BR_AGEING_TIME is a u32)
                ageing_time = utils.parse_uint(value, bit_size=32)
            except ValueError as e:
                raise LinkOptionError(f"Invalid `ageing_time` (centiseconds) on collision domain `{self.name}`: {e}")

            self.meta[name] = ageing_time
            return old_value

        if name == 'group_fwd_mask':
            try:
                # Limit accepted by the Linux bridge (IFLA_BR_GROUP_FWD_MASK is a u16)
                group_fwd_mask = utils.parse_uint(value, bit_size=16)
            except ValueError as e:
                raise LinkOptionError(f"Invalid `group_fwd_mask` on collision domain `{self.name}`: {e}")
            # STP, MAC Pause and LACP frames cannot be forwarded (BR_GROUPFWD_RESTRICTED)
            if group_fwd_mask & 0x0007:
                raise LinkOptionError(
                    f"Invalid `group_fwd_mask` on collision domain `{self.name}`: "
                    f"bits 0-2 (STP, MAC Pause and LACP) cannot be set."
                )

            self.meta[name] = group_fwd_mask
            return old_value

        self.meta[name] = value
        return old_value

    def check(self, strict: bool = True) -> None:
        """Check if the collision domain satisfies the constraints of its type.

        A point-to-point collision domain must have exactly two endpoints and cannot have external interfaces.
        `ageing_time` and `group_fwd_mask` can only be used on `bridge` collision domains.

        Args:
            strict (bool): If False, a point-to-point collision domain can have less than two endpoints, since they
                can be connected later. More than two endpoints are never allowed. Default: True.

        Returns:
            None

        Raises:
            LinkInvalidError: If the collision domain does not satisfy the constraints of its type.
        """
        if self.is_p2p():
            if len(self.meta['external']) > 0:
                raise LinkInvalidError(
                    f"Point-to-point collision domain `{self.name}` cannot have external interfaces."
                )

            if len(self.machines) > 2 or (strict and len(self.machines) != 2):
                raise LinkInvalidError(
                    f"Point-to-point collision domain `{self.name}` must have exactly two endpoints, "
                    f"found {len(self.machines)}."
                )

        if not self.is_bridge() and ('ageing_time' in self.meta or 'group_fwd_mask' in self.meta):
            raise LinkInvalidError(
                f"`ageing_time` and `group_fwd_mask` can only be used on `bridge` collision domains, "
                f"`{self.name}` must explicitly declare `type=\"bridge\"`."
            )

    def is_bridge(self) -> bool:
        """Check if the collision domain is bridge.

        Returns:
            bool: If the collision domain is bridge.
        """
        return self.meta['type'] == CollisionDomainTypesOption.BRIDGE

    def is_hub(self) -> bool:
        """Check if the collision domain is hub.

        Returns:
            bool: If the collision domain is hub.
        """
        return self.meta['type'] == CollisionDomainTypesOption.HUB

    def is_p2p(self) -> bool:
        """Check if the collision domain is point-to-point.

        Returns:
            bool: If the collision domain is point-to-point.
        """
        return self.meta['type'] == CollisionDomainTypesOption.P2P

    def __repr__(self) -> str:
        return "Link(%s, %s)" % (self.name, self.meta)
