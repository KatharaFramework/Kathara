import json
from typing import Dict, Any

from ....foundation.manager.stats.ILinkStats import ILinkStats


class KubernetesLinkStats(ILinkStats):
    """The class responsible to handle Kubernetes Networks statistics.

    Attributes:
        link_api_object (Any): The Kubernetes Network associated with this statistics.
        lab_hash (str): The hash identifier of the network scenario of the Kubernetes Network.
        name (str): The name of the collision domain.
        network_name (str): The Kubernetes Network Name.
        vxlan_id (str): The VXLAN Identifier associated to this network.
    """
    __slots__ = ['link_api_object', 'lab_hash', 'name', 'network_name', 'vxlan_id']

    def __init__(self, link_api_object: Any):
        self.link_api_object: Any = link_api_object
        self.lab_hash: str = link_api_object['metadata']['namespace']
        self.name: str = link_api_object['metadata']['labels']['name']
        self.network_name: str = link_api_object['metadata']['name']
        self.vxlan_id = json.loads(link_api_object['spec']['config'])['vxlanId']

    def update(self) -> None:
        """Update dynamic statistics with the current ones.

        Returns:
            None
        """
        return

    def to_dict(self) -> Dict[str, Any]:
        """Transform statistics into a dict representation.

        Returns:
            Dict[str, Any]: Dict containing statistics.
        """
        return {
            "network_scenario_id": self.lab_hash,
            "name": self.name,
            "network_name": self.network_name,
            "vxlan_id": self.vxlan_id
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
        formatted_stats += f"\nVXLAN ID: {self.vxlan_id}"

        return formatted_stats
