from typing import Optional, Dict, Any

from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "hosthome_mount": False,
    "shared_mount": True,
    "image_update_policy": "Prompt",
    "shared_cd": False,
    "remote_url": None,
    "cert_path": None,
    "network_plugin": "kathara/katharanp_vde"
}


class DockerSettingsAddon(SettingsAddon):
    __slots__ = ['hosthome_mount', 'shared_mount', 'image_update_policy', 'shared_cd', 'remote_url', 'cert_path',
                 'network_plugin']

    def __init__(self) -> None:
        self.hosthome_mount: bool = False
        self.shared_mount: bool = True
        self.image_update_policy: str = 'Prompt'
        self.shared_cd: bool = False
        self.remote_url: Optional[str] = None
        self.cert_path: Optional[str] = None
        self.network_plugin: Optional[str] = "kathara/katharanp_vde"

    def _to_dict(self) -> Dict[str, Any]:
        return {
            'hosthome_mount': self.hosthome_mount,
            'shared_mount': self.shared_mount,
            'image_update_policy': self.image_update_policy,
            'shared_cd': self.shared_cd,
            'remote_url': self.remote_url,
            'cert_path': self.cert_path,
            'network_plugin': self.network_plugin
        }
