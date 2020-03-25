from ..factory.Factory import Factory


class SettingsAddonFactory(Factory):
    def __init__(self):
        self.module_template = "Resources.setting.addon"
        self.name_template = "%sSettingsAddon"
