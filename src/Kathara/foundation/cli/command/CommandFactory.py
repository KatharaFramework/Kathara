from ...factory.Factory import Factory


class CommandFactory(Factory):
    def __init__(self) -> None:
        self.module_template = "Kathara.cli.command"
        self.name_template = "%sCommand"
