from typing import Dict, Any, Generator, Optional

from podman.domain.containers import Container
from podman.errors import NotFound

from ....decorators import privileged
from ....foundation.manager.stats.IMachineStats import IMachineStats
from ....utils import human_readable_bytes
from ..interfaces import parse_iface_alias
from ..libpod_compat import LibpodCompat


class PodmanMachineStats(IMachineStats):
    """The class responsible to handle Podman Machine statistics.

    Attributes:
        machine_api_object (Container): The Podman Container associated with this statistics.
        stats (Generator[Dict[str, Any], None, None]): A generator containing dicts with the Podman statistics
        lab_hash (str): The hash identifier of the network scenario of the Podman Container.
        name (str): The name of the device.
        container_name (str): The Podman Container Name.
        user (str): The user that deployed the associated Podman Network.
        image (str): The Podman Image used for deploying the Podman Container.
        status (Optional[str]): The status of the Podman Container.
        pids (Optional[int]): The number of PIDs associated with the Podman Container.
        interfaces (str): The interfaces connected to this Podman Container.
        cpu_usage (str): The cpu usage of the Podman Container.
        mem_usage (str): The memory usage of the Podman Container.
        mem_percent (str): The memory usage of the Podman Container as a percentage.
        net_usage (str): The network usage of the Podman Container.
    """
    __slots__ = ['machine_api_object', 'stats', 'lab_hash', 'name', 'container_name', 'user', 'status', 'image',
                 'pids', 'cpu_usage', 'mem_usage', 'mem_percent', 'net_usage', '_prev_stats']

    def __init__(self, machine_api_object: Container):
        self.machine_api_object: Container = machine_api_object
        self.stats: Generator[Dict[str, Any], None, None] = machine_api_object.stats(stream=True, decode=True)
        self._prev_stats: Optional[Dict[str, Any]] = None
        # Static Information
        self.lab_hash: str = machine_api_object.labels['lab_hash']
        self.name: str = machine_api_object.labels['name']
        self.container_name: str = machine_api_object.name
        self.user: Optional[str] = machine_api_object.labels['user']
        self.image: str = machine_api_object.image.tags[0]
        # Dynamic Information
        self.status: Optional[str] = None
        self.pids: Optional[int] = None
        self.interfaces: str = "-"
        self.cpu_usage: str = "-"
        self.mem_usage: str = "- / -"
        self.mem_percent: str = "-"
        self.net_usage: str = "-"

        self.update()

    @privileged
    def update(self) -> None:
        """Update dynamic statistics with the current ones.

        Returns:
            None
        """
        updated_stats = next(self.stats)
        try:
            self.machine_api_object.reload()
        except NotFound:
            # Happens while deleting
            pass
        if updated_stats.get("Error") or not updated_stats.get("Stats"):
            return
        entry = updated_stats["Stats"][0]

        self.status = LibpodCompat.container_status(self.machine_api_object)
        self.pids = entry.get("PIDs", 0)

        # Native libpod network-attachment data has no equivalent of Docker's endpoint DriverOpts: the
        # interface number is read back from the `kathara-eth<N>` alias of each attachment instead
        # (see PodmanMachine.get_container_ifaces), and the link name from the attached network's
        # `name` label.
        ifaces = {}
        attached_networks = self.machine_api_object.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}
        for network_name, net_settings in attached_networks.items():
            iface_num = next((num for num in map(parse_iface_alias, net_settings.get("Aliases") or [])
                              if num is not None), None)
            if iface_num is None:
                continue

            try:
                network = self.machine_api_object.podman_client.networks.get(network_name)
            except NotFound:
                continue
            link_name = network.attrs.get("labels", {}).get("name")
            if link_name:
                ifaces[link_name] = iface_num

        if 'bridged_iface' in self.machine_api_object.labels:
            ifaces["Bridged"] = int(self.machine_api_object.labels['bridged_iface'])

        if ifaces:
            self.interfaces = ", ".join(sorted([f"{num}:{link_name}" for link_name, num in ifaces.items()]))
        else:
            self.interfaces = "-"

        # CPU is already a percentage computed by Podman between two samples (no deltas needed, unlike Docker).
        self.cpu_usage = f"{entry.get('CPU', 0):.2f}%"

        usage, limit = entry.get("MemUsage", 0), entry.get("MemLimit", 0)
        self.mem_usage = human_readable_bytes(usage) + " / " + human_readable_bytes(limit)
        self.mem_percent = f"{entry.get('MemPerc', 0):.2f} %"

        networks = entry.get("Network") or {}
        rx_bytes = sum(net.get("RxBytes", 0) for net in networks.values())
        tx_bytes = sum(net.get("TxBytes", 0) for net in networks.values())
        self.net_usage = human_readable_bytes(rx_bytes) + " / " + human_readable_bytes(tx_bytes)

    def to_dict(self) -> Dict[str, Any]:
        """Transform statistics into a dict representation.

        Returns:
            Dict[str, Any]: Dict containing statistics.
        """
        return {
            "network_scenario_id": self.lab_hash,
            "name": self.name,
            "container_name": self.container_name,
            "user": self.user,
            "status": self.status,
            "image": self.image,
            "pids": self.pids,
            "cpu_usage": self.cpu_usage,
            "mem_usage": self.mem_usage,
            "mem_percent": self.mem_percent,
            "net_usage": self.net_usage,
            'interfaces': self.interfaces,
        }

    def __repr__(self) -> str:
        return str(self.to_dict())

    def __str__(self) -> str:
        """Return a formatted string with the device statistics.

        Returns:
           str: A formatted string with the device statistics
        """
        formatted_stats = f"Network Scenario ID: {self.lab_hash}\n"
        formatted_stats += f"Device Name: {self.name}\n"
        formatted_stats += f"Container Name: {self.container_name}\n"
        formatted_stats += f"Status: {self.status}\n"
        formatted_stats += f"Image: {self.image}\n"
        formatted_stats += f"PIDs: {self.pids}\n"
        formatted_stats += f"CPU Usage: {self.cpu_usage}\n"
        formatted_stats += f"Memory Usage: {self.mem_usage}\n"
        formatted_stats += f"Network Usage (DL/UL): {self.net_usage}"
        formatted_stats += f"Interfaces: {self.interfaces}\n"

        return formatted_stats
