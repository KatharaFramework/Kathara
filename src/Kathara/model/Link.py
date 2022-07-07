from typing import List, Any, Dict

from . import Lab as LabPackage
from . import Machine as MachinePackage
from .ExternalLink import ExternalLink

BRIDGE_LINK_NAME = "kathara_host_bridge"


class Link(object):
    """A Kathara collision domain.

    Contains information about the collision domain and the API object to interact with the Manager.

    Attributes:
        lab (Kathara.model.Lab.Lab): The Kathara network scenario of the collision domain.
        name (str): The name of the collision domain.
        external (List[Kathara.model.ExternalLink.ExternalLink]): External links attached to this collision domain.
        machines (Dict[str, Kathara.model.Machine.Machine]): Machines attached to this collision domain.
        api_object (Any): To interact with the current Kathara Manager.
    """
    __slots__ = ['lab', 'name', 'external', 'machines', 'api_object']

    def __init__(self, lab: 'LabPackage.Lab', name) -> None:
        self.lab: 'LabPackage.Lab' = lab
        self.name: str = name
        self.external: List[ExternalLink] = []
        self.machines: Dict[str, 'MachinePackage.Machine'] = {}
        self.api_object: Any = None

    def __repr__(self) -> str:
        return "Link(%s, %s)" % (self.name, self.external)
