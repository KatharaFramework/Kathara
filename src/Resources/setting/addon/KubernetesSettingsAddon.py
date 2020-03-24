from ...foundation.setting.SettingsAddon import SettingsAddon


class KubernetesSettingsAddon(SettingsAddon):
    __slots__ = ['api_server_url', 'api_key']

    def __init__(self):
        self.api_server_url = "localhost"
        self.api_key = "fruskit"

    def _to_dict(self):
        return {
            'api_server_url': self.api_server_url,
            'api_key': self.api_key
        }
