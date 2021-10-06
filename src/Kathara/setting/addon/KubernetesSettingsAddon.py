from typing import Optional, Dict, Any

from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "api_server_url": "Empty String",
    "api_token": "Empty String",
    "host_shared": True,
    "image_pull_policy": "IfNotPresent"
}


class KubernetesSettingsAddon(SettingsAddon):
    __slots__ = ['api_server_url', 'api_token', 'host_shared', 'image_pull_policy']

    def __init__(self) -> None:
        self.api_server_url: Optional[str] = None
        self.api_token: Optional[str] = None
        self.host_shared: bool = True
        self.image_pull_policy: Optional[str] = "IfNotPresent"

    def _to_dict(self) -> Dict[str, Any]:
        return {
            'api_server_url': self.api_server_url,
            'api_token': self.api_token,
            'host_shared': self.host_shared,
            'image_pull_policy': self.image_pull_policy
        }
