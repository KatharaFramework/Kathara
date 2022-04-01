from typing import Dict, Any, List

from docker.models.containers import Container
from docker.models.networks import Network

from ....foundation.manager.stats.ILinkStats import ILinkStats


class DockerLinkStats(ILinkStats):
    """The class responsible to handle Docker Networks statistics.

    Attributes:
        link_api_object (Network): The Docker Network associated with this statistics.
        lab_hash (str): The hash identifier of the network scenario of the Docker Network.
        name (str): The name of the collision domain.
        network_id (str): The Docker Network ID.
        user (str): The user that deployed the associated Docker Network.
        enable_ipv6 (bool): True if ipv6 is enabled, else None.
        external (List[str]): A list with the name of the attached external networks.
        containers (List[Container]): A list of the Docker Container associated with the Docker Network.
    """
    __slots__ = ['link_api_object', 'lab_hash', 'name', 'network_id', 'user', 'enable_ipv6', 'external', 'containers']

    def __init__(self, link_api_object: Network):
        self.link_api_object: Network = link_api_object
        self.lab_hash: str = link_api_object.attrs.get('Labels')['lab_hash']
        self.name: str = link_api_object.attrs.get('Labels')['name']
        self.network_id: str = link_api_object.name
        self.user: str = link_api_object.attrs.get('Labels')['user']
        self.enable_ipv6: bool = link_api_object.attrs.get('EnableIPv6')
        external = link_api_object.attrs.get('Labels')['external']
        self.external: List[str] = external.split(";") if external else []
        self.containers: List[Container] = []
        self.update()

    def update(self) -> None:
        """
        Update dynamic statistics with the current ones.

        Returns:
            None
        """
        self.link_api_object.reload()
        self.containers = [container for container in self.link_api_object.containers]

    def to_dict(self) -> Dict[str, Any]:
        self.update()
        return {
            "network_scenario_id": self.lab_hash,
            "name": self.name,
            "network_id": self.network_id,
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
           str: a formatted string with the device statistics
        """
        formatted_stats = f"Network Scenario ID: {self.lab_hash}"
        formatted_stats += f"\nLink Name: {self.name}"
        formatted_stats += f"\nNetwork Name: {self.network_id}"
        formatted_stats += f"\nEnable IPv6: {self.enable_ipv6}"
        if self.external:
            formatted_stats += f"\nExternals:"
            for ext in self.external:
                formatted_stats += f"\n\t{ext}\n"
        if self.containers:
            formatted_stats += f"\nContainers:"
            for container in self.containers:
                formatted_stats += f"\n\t{container.labels['name']}: {container}"

        return formatted_stats
