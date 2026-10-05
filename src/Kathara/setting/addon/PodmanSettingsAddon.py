from typing import Optional, Dict, Any

from ...exceptions import SettingsError
from ...foundation.setting.SettingsAddon import SettingsAddon
from ...types import SharedCollisionDomainsOption

DEFAULTS = {
    "hosthome_mount": False,
    "shared_mount": True,
    "image_update_policy": "Prompt",
    "shared_cds": SharedCollisionDomainsOption.NOT_SHARED,
    "api_socket_url": None,
    "network_plugin": "katharanp_vde",
}

AVAILABLE_NETWORK_PLUGINS = ("katharanp_vde", "katharanp")


class PodmanSettingsAddon(SettingsAddon):
    __slots__ = ['hosthome_mount', 'shared_mount', 'image_update_policy', 'shared_cds', 'api_socket_url',
                 'network_plugin']

    def __init__(self) -> None:
        self.hosthome_mount: bool = False
        self.shared_mount: bool = True
        self.image_update_policy: str = 'Prompt'
        self.shared_cds: int = SharedCollisionDomainsOption.NOT_SHARED
        # URL of the local Podman service socket (e.g. unix:///run/user/1000/podman/podman.sock).
        # Only local `unix://` sockets are supported (remote connections cannot install the network plugin).
        # If None, PodmanManager resolves the default rootless user socket.
        self.api_socket_url: Optional[str] = None
        # Name of the netavark plugin (driver) used to create the collision domains.
        self.network_plugin: str = "katharanp_vde"

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'network_plugin' and value not in AVAILABLE_NETWORK_PLUGINS:
            raise SettingsError("Network Plugin must be one of the following: %s." %
                                ", ".join(AVAILABLE_NETWORK_PLUGINS))

        super().__setattr__(name, value)

    def _to_dict(self) -> Dict[str, Any]:
        return {
            'hosthome_mount': self.hosthome_mount,
            'shared_mount': self.shared_mount,
            'image_update_policy': self.image_update_policy,
            'shared_cds': self.shared_cds,
            'api_socket_url': self.api_socket_url,
            'network_plugin': self.network_plugin
        }
