from ..factory.Factory import Factory


class ManagerFactory(Factory):
    def __init__(self) -> None:
        self.module_template: str = "Kathara.manager.%s"
        self.name_template: str = "%sManager"
