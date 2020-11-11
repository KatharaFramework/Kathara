from ...factory.Factory import Factory


class CommandFactory(Factory):
    def __init__(self):
        self.module_template = "Resources.cli.command"
        self.name_template = "%sCommand"
