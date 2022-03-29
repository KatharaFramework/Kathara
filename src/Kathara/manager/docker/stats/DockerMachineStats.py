from typing import Dict, Any

from docker.models.containers import Container

from ....foundation.manager.stats.IMachineStats import IMachineStats
from ....utils import human_readable_bytes


class DockerMachineStats(IMachineStats):
    """The class responsible to handle Docker Machine statistics."""
    __slots__ = ['machine_api_object', 'stats', 'real_lab_hash', 'name', 'real_name', 'user', 'status', 'image',
                 'pids', 'cpu_usage', 'mem_usage', 'mem_percent', 'net_usage']

    def __init__(self, machine_api_object: Container):
        self.machine_api_object = machine_api_object
        self.stats = machine_api_object.stats(stream=True)
        # Static Information
        self.real_lab_hash = machine_api_object.labels['lab_hash']
        self.name = machine_api_object.labels['name']
        self.real_name = machine_api_object.name
        self.user = machine_api_object.labels['user']
        self.image = machine_api_object.image.tags[0]
        # Dynamic Information
        self.status = None
        self.pids = None
        self.cpu_usage = "-"
        self.mem_usage = "- / -"
        self.mem_percent = "-"
        self.net_usage = "-"

        self.update()

    def update(self) -> None:
        """
        Update dynamic statistics with the current ones.

        Returns:
            None
        """
        updated_stats = next(self.stats)
        self.status = self.machine_api_object.status
        self.pids = updated_stats['pids_stats']['current'] if 'current' in updated_stats['pids_stats'] else 0
        if "system_cpu_usage" in updated_stats["cpu_stats"]:
            cpu_usage = updated_stats["cpu_stats"]["cpu_usage"]["total_usage"] / \
                        updated_stats["cpu_stats"]["system_cpu_usage"]
            self.cpu_usage = f"{cpu_usage:.2f}%"

        if "usage" in updated_stats["memory_stats"]:
            usage = updated_stats["memory_stats"]["usage"]
            limit = updated_stats["memory_stats"]["limit"]
            self.mem_usage = human_readable_bytes(usage) + " / " + human_readable_bytes(limit)
            self.mem_percent = f"{((usage / limit) * 100):.2f}"

        if "networks" in updated_stats:
            network_stats = updated_stats["networks"] if "networks" in updated_stats else {}
            rx_bytes = sum([net_stats["rx_bytes"] for (_, net_stats) in network_stats.items()])
            tx_bytes = sum([net_stats["tx_bytes"] for (_, net_stats) in network_stats.items()])
            self.net_usage = human_readable_bytes(rx_bytes) + " / " + human_readable_bytes(tx_bytes)

    def get_formatted_stats(self) -> str:
        """
        Return a formatted string with the device statistics.

        Returns:
            str: a formatted string with the device statistics
        """
        formatted_stats = f"Lab Hash: {self.real_lab_hash}\n"
        formatted_stats += f"Device Name: {self.name}\n"
        formatted_stats += f"Container Name: {self.real_name}\n"
        formatted_stats += f"Status: {self.status}\n"
        formatted_stats += f"Image: {self.image}\n\n"
        formatted_stats += f"PIDs: {self.pids}\n"
        formatted_stats += f"CPU Usage: {self.cpu_usage}\n"
        formatted_stats += f"Memory Usage: {self.mem_usage}\n"
        formatted_stats += f"Network Usage (DL/UL): {self.net_usage}\n"

        return formatted_stats

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "real_lab_hash": self.real_lab_hash,
            "name": self.name,
            "real_name": self.real_name,
            "user": self.user,
            "status": self.status,
            "image": self.image,
            "pids": self.pids,
            "cpu_usage": self.cpu_usage,
            "mem_usage": self.mem_usage,
            "mem_percent": self.mem_percent,
            "net_usage": self.net_usage
        }

    def __repr__(self) -> str:
        return str(self._to_dict())

    def __str__(self) -> str:
        return self.get_formatted_stats()
