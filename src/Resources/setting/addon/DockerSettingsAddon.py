from ...foundation.setting.SettingsAddon import SettingsAddon

DEFAULTS = {
    "hosthome_mount": False,
    "shared_mount": True,
    "api_server_url": None,
    "cert_path": None
}


class DockerSettingsAddon(SettingsAddon):
    __slots__ = ['hosthome_mount', 'shared_mount', 'api_server_url', 'cert_path']

    def __init__(self):
        self.hosthome_mount = False
        self.shared_mount = True
        self.api_server_url = None
        self.cert_path = None

    def _to_dict(self):
        return {
            'hosthome_mount': self.hosthome_mount,
            'shared_mount': self.shared_mount,
            'api_server_url': self.api_server_url,
            'cert_path': self.cert_path
        }
