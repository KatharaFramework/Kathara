from typing import List, Any, Dict, Optional, Union

from . import Lab as LabPackage
from . import Machine as MachinePackage
from .ExternalLink import ExternalLink
from ..types import CollisionDomainTypesOption

BRIDGE_LINK_NAME = "kathara_host_bridge"


class Link(object):
    """A Kathara collision domain.

    Contains information about the collision domain and the API object to interact with the Manager.

    Attributes:
        lab (Kathara.model.Lab.Lab): The Kathara network scenario of the collision domain.
        name (str): The name of the collision domain.
        external (List[Kathara.model.ExternalLink.ExternalLink]): External links attached to this collision domain.
        type (Optional[CollisionDomainTypesOption]): Type of the collision domain.
        machines (Dict[str, Kathara.model.Machine.Machine]): Machines attached to this collision domain.
        api_object (Any): To interact with the current Kathara Manager.
    """
    __slots__ = ['lab', 'name', 'external', 'machines', 'api_object', '_type']

    def __init__(self, lab: 'LabPackage.Lab', name) -> None:
        self.lab: 'LabPackage.Lab' = lab
        self.name: str = name
        self.external: List[ExternalLink] = []
        self.machines: Dict[str, 'MachinePackage.Machine'] = {}
        self.api_object: Any = None

        self._type: Optional[CollisionDomainTypesOption] = None

    @property
    def type(self) -> Optional[CollisionDomainTypesOption]:
        """Get the collision domain type.

        Returns:
            Optional[CollisionDomainTypesOption]: The link type.
        """
        return self._type

    @type.setter
    def type(self, value: Optional[Union[str, CollisionDomainTypesOption]]) -> None:
        """Set the collision domain type. `None` means the default one.

        Raises:
            ValueError: If the value is not a supported collision domain type.
        """
        self._type = CollisionDomainTypesOption.parse(value) if value is not None else None

    def __repr__(self) -> str:
        return "Link(%s, %s, %s)" % (self.name, self.type, self.external)
