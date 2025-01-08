import json
from typing import Dict, Any, Optional

from kubernetes.client import V1Pod

from ....foundation.manager.stats.IMachineStats import IMachineStats


class KubernetesMachineStats(IMachineStats):
    """The class responsible to handle Kubernetes Machine statistics.

    Attributes:
        machine_api_object (V1Pod): The Kubernetes Pod associated with this statistics.
        lab_hash (str): The hash identifier of the network scenario of the Kubernetes Pod.
        name (str): The name of the device.
        pod_name (str): The Kubernetes Pod Name.
        image (str): The Image used for deploying the Kubernetes Pod.
        interfaces (str): The interfaces connected to this Kubernetes Pod.
        status (Optional[str]): The status of the Kubernetes Pod.
        assigned_node (Optional[str]): The cluster node assigned to this Kubernetes Pod.
    """
    __slots__ = ['machine_api_object', 'lab_hash', 'name', 'pod_name', 'image', 'status', 'assigned_node']

    def __init__(self, machine_api_object: V1Pod):
        self.machine_api_object: V1Pod = machine_api_object
        # Static Information
        self.lab_hash: str = machine_api_object.metadata.namespace
        self.name: str = machine_api_object.metadata.labels["name"]
        self.pod_name: str = machine_api_object.metadata.name

        container_statuses = machine_api_object.status.container_statuses
        self.image: str = container_statuses[0].image if container_statuses else "N/A"

        interfaces = []
        pod_networks_conf = json.loads(self.machine_api_object.metadata.annotations["k8s.v1.cni.cncf.io/networks"])
        for idx, network_conf in enumerate(pod_networks_conf):
            if 'kathara.link' in network_conf:
                interfaces.append(f"{idx}:{network_conf['kathara.link']}")
        self.interfaces: str = "-" if not interfaces else ", ".join(interfaces)

        # Dynamic Information
        self.status: Optional[str] = None
        self.assigned_node: Optional[str] = None

        self.update()

    def update(self) -> None:
        """Update dynamic statistics with the current ones.

        Returns:
            None
        """
        self.status = self._get_detailed_machine_status(self.machine_api_object)
        self.assigned_node = self.machine_api_object.spec.node_name

    @staticmethod
    def _get_detailed_machine_status(pod_api_object: V1Pod) -> str:
        """Return a string containing the Kubernetes Pod status.

        Args:
            pod_api_object (client.V1Pod): A Kubernetes Pod.

        Returns:
            str: A string containing the Kubernetes Pod status.
        """
        container_statuses = pod_api_object.status.container_statuses

        if not container_statuses:
            return pod_api_object.status.phase

        container_status = container_statuses[0].state

        string_status = None
        if container_status.terminated is not None:
            string_status = container_status.terminated.reason if container_status.terminated.reason is not None \
                else "Terminating"
        elif container_status.waiting is not None:
            string_status = container_status.waiting.reason

        # In case the status contains an error message, split it to the first ": " and take the left part
        return string_status.split(': ')[0] if string_status is not None else pod_api_object.status.phase

    def to_dict(self) -> Dict[str, Any]:
        """Transform statistics into a dict representation.

        Returns:
            Dict[str, Any]: Dict containing statistics.
        """
        return {
            "network_scenario_id": self.lab_hash,
            "name": self.name,
            "pod_name": self.pod_name,
            "image": self.image,
            "status": self.status,
            "assigned_node": self.assigned_node,
            "interfaces": self.interfaces,
        }

    def __repr__(self) -> str:
        return str(self.to_dict())

    def __str__(self) -> str:
        """Return a formatted string with the device statistics.

        Returns:
           str: a formatted string with the device statistics
        """
        formatted_stats = f"Network Scenario ID: {self.lab_hash}\n"
        formatted_stats += f"Device Name: {self.name}\n"
        formatted_stats += f"Pod Name: {self.pod_name}\n"
        formatted_stats += f"Image: {self.image}\n"
        formatted_stats += f"Status: {self.status}\n"
        formatted_stats += f"Assigned Node: {self.assigned_node}"
        formatted_stats += f"Interfaces: {self.interfaces}\n"

        return formatted_stats
