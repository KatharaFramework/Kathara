from ....factory.Factory import Factory


class OptionsHandlerFactory(Factory):
    def __init__(self) -> None:
        self.module_template: str = "Kathara.cli.ui.setting"
        self.name_template: str = "%sOptionsHandler"
