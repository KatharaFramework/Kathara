from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "api_server_url": "Empty String",
    "api_token": "Empty String",
    "host_shared": True,
    "image_pull_policy": "IfNotPresent"
}


class KubernetesSettingsAddon(SettingsAddon):
    __slots__ = ['api_server_url', 'api_token', 'host_shared', 'image_pull_policy']

    def __init__(self):
        self.api_server_url = None
        self.api_token = None
        self.host_shared = True
        self.image_pull_policy = "IfNotPresent"

    def _to_dict(self):
        return {
            'api_server_url': self.api_server_url,
            'api_token': self.api_token,
            'host_shared': self.host_shared,
            'image_pull_policy': self.image_pull_policy
        }
