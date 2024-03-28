from typing import Optional, Dict, Any

from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "api_server_url": "Empty String",
    "api_token": "Empty String",
    "host_shared": True,
    "image_pull_policy": "IfNotPresent",
    "private_registry_dockerconfigjson": "Empty String"
}


class KubernetesSettingsAddon(SettingsAddon):
    __slots__ = ['api_server_url', 'api_token', 'host_shared', 'image_pull_policy', 'private_registry_dockerconfigjson']

    def __init__(self) -> None:
        self.api_server_url: Optional[str] = None
        self.api_token: Optional[str] = None
        self.host_shared: bool = True
        self.image_pull_policy: Optional[str] = "IfNotPresent"
        self.private_registry_dockerconfigjson: Optional[str] = None

    def _to_dict(self) -> Dict[str, Any]:
        return {
            'api_server_url': self.api_server_url,
            'api_token': self.api_token,
            'host_shared': self.host_shared,
            'image_pull_policy': self.image_pull_policy,
            'private_registry_dockerconfigjson': self.private_registry_dockerconfigjson
        }
