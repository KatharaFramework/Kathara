from typing import Optional, Dict, Any

from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "hosthome_mount": False,
    "shared_mount": True,
    "shared_cd": False,
    "remote_url": None,
    "cert_path": None
}


class DockerSettingsAddon(SettingsAddon):
    __slots__ = ['hosthome_mount', 'shared_mount', 'shared_cd', 'remote_url', 'cert_path']

    def __init__(self) -> None:
        self.hosthome_mount: bool = False
        self.shared_mount: bool = True
        self.shared_cd: bool = False
        self.remote_url: Optional[str] = None
        self.cert_path: Optional[str] = None

    def _to_dict(self) -> Dict[str, Any]:
        return {
            'hosthome_mount': self.hosthome_mount,
            'shared_mount': self.shared_mount,
            'shared_cd': self.shared_cd,
            'remote_url': self.remote_url,
            'cert_path': self.cert_path
        }
