from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "api_server_url": "Empty String",
    "api_token": "Empty String",
    "host_shared": True
}


class KubernetesSettingsAddon(SettingsAddon):
    __slots__ = ['api_server_url', 'api_token', 'host_shared']

    def __init__(self):
        self.api_server_url = None
        self.api_token = None
        self.host_shared = True

    def _to_dict(self):
        return {
            'api_server_url': self.api_server_url,
            'api_token': self.api_token,
            'host_shared': self.host_shared,
        }
