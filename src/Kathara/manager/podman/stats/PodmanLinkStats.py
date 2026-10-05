from typing import Dict, Any, List

from podman.domain.containers import Container
from podman.domain.networks import Network
from podman.errors import NotFound

from ....foundation.manager.stats.ILinkStats import ILinkStats


class PodmanLinkStats(ILinkStats):
    """The class responsible to handle Podman Networks statistics.

    Attributes:
        link_api_object (Network): The Podman Network associated with this statistics.
        lab_hash (str): The hash identifier of the network scenario of the Podman Network.
        name (str): The name of the collision domain.
        network_name (str): The Podman Network Name.
        user (str): The user that deployed the associated Podman Network.
        enable_ipv6 (bool): True if ipv6 is enabled, else None.
        external (List[str]): A list with the name of the attached external networks.
        containers (List[Container]): A list of the Podman Container associated with the Podman Network.
    """
    __slots__ = ['link_api_object', 'lab_hash', 'name', 'network_name', 'user', 'enable_ipv6', 'external', 'containers']

    def __init__(self, link_api_object: Network):
        self.link_api_object: Network = link_api_object
        labels = link_api_object.attrs.get('labels') or {}
        self.lab_hash: str = labels.get('lab_hash')
        self.name: str = labels.get('name')
        self.network_name: str = link_api_object.name
        self.user: str = labels.get('user')
        self.enable_ipv6: bool = link_api_object.attrs.get('ipv6_enabled', False)
        external = labels.get('external')
        self.external: List[str] = external.split(";") if external else []
        self.containers: List[Container] = []
        self.update()

    def update(self) -> None:
        """Update dynamic statistics with the current ones.

        Returns:
            None
        """
        try:
            self.link_api_object.reload()
        except NotFound:
            # Happens while deleting
            pass

        self.containers = [container for container in self.link_api_object.containers]

    def to_dict(self) -> Dict[str, Any]:
        """Transform statistics into a dict representation.

        Returns:
            Dict[str, Any]: Dict containing statistics.
        """
        return {
            "network_scenario_id": self.lab_hash,
            "name": self.name,
            "network_name": self.network_name,
            "user": self.user,
            "enable_ipv6": self.enable_ipv6,
            "external": self.external,
            "containers": self.containers
        }

    def __repr__(self) -> str:
        return str(self.to_dict())

    def __str__(self) -> str:
        """Return a formatted string with the link statistics.

        Returns:
           str: A formatted string with the link statistics
        """
        formatted_stats = f"Network Scenario ID: {self.lab_hash}"
        formatted_stats += f"\nLink Name: {self.name}"
        formatted_stats += f"\nNetwork Name: {self.network_name}"
        formatted_stats += f"\nEnable IPv6: {self.enable_ipv6}"
        if self.external:
            formatted_stats += f"\nExternal Interfaces:"
            for ext in self.external:
                formatted_stats += f"\n\t- {ext}\n"
        if self.containers:
            formatted_stats += f"\nAttached Devices:"
            for container in self.containers:
                formatted_stats += f"\n\t- {container.labels['name']}"

        return formatted_stats
