from ....factory.Factory import Factory


class OptionsHandlerFactory(Factory):
    def __init__(self):
        self.module_template = "Kathara.cli.ui.setting"
        self.name_template = "%sOptionsHandler"
