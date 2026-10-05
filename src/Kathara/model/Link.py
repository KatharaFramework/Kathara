from typing import List, Any, Dict, Optional, Union

from . import Lab as LabPackage
from . import Machine as MachinePackage
from .ExternalLink import ExternalLink
from ..exceptions import LinkModeError
from ..types import LinkMode

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
        mode (Optional[Kathara.types.LinkMode]): The behaviour of the collision domain (hub, switch or managed
            switch). If None, it is a hub when it is created, and it keeps its mode when it is already deployed.
    """
    __slots__ = ['lab', 'name', 'external', 'machines', 'api_object', '_mode']

    def __init__(self, lab: 'LabPackage.Lab', name, mode: Optional[Union[LinkMode, str]] = None) -> None:
        self.lab: 'LabPackage.Lab' = lab
        self.name: str = name
        self.external: List[ExternalLink] = []
        self.machines: Dict[str, 'MachinePackage.Machine'] = {}
        self.api_object: Any = None
        self._mode: Optional[LinkMode] = None

        self.mode = mode

    @property
    def mode(self) -> Optional[LinkMode]:
        return self._mode

    @mode.setter
    def mode(self, value: Optional[Union[LinkMode, str]]) -> None:
        if value is not None:
            try:
                value = LinkMode(value.lower() if isinstance(value, str) else value)
            except ValueError:
                raise LinkModeError(
                    f"Mode `{value}` of collision domain `{self.name}` is invalid, "
                    f"it must be one of: {', '.join([x.value for x in LinkMode])}."
                )

        self._mode = value

    def is_managed(self) -> bool:
        """Check if the collision domain is a managed switch.

        Returns:
            bool: True if the mode of the collision domain is `managed`.
        """
        return self._mode == LinkMode.MANAGED

    def __repr__(self) -> str:
        return "Link(%s, %s)" % (self.name, self.external)
