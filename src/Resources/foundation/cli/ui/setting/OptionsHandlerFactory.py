from ....factory.Factory import Factory


class OptionsHandlerFactory(Factory):
    def __init__(self):
        self.module_template = "Resources.cli.ui.setting"
        self.name_template = "%sOptionsHandler"
