from ...foundation.setting.SettingsAddon import SettingsAddon


class DockerSettingsAddon(SettingsAddon):
    __slots__ = ['hosthome_mount', 'shared_mount']

    def __init__(self):
        self.hosthome_mount = False
        self.shared_mount = True

    def _to_dict(self):
        return {
            'hosthome_mount': self.hosthome_mount,
            'shared_mount': self.shared_mount
        }
