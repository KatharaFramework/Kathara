from ..factory.Factory import Factory


class SettingsAddonFactory(Factory):
    def __init__(self) -> None:
        self.module_template: str = "Kathara.setting.addon"
        self.name_template: str = "%sSettingsAddon"
