from ..factory.Factory import Factory


class ManagerFactory(Factory):
    def __init__(self):
        self.module_template = "Resources.manager.%s"
        self.name_template = "%sManager"
