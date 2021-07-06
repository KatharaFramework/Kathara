class CliArgs(object):
    __slots__ = ['args']

    __instance = None

    @staticmethod
    def get_instance():
        if CliArgs.__instance is None:
            CliArgs()

        return CliArgs.__instance

    def __init__(self):
        if CliArgs.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.args = {}

            CliArgs.__instance = self

    def __getattr__(self, item):
        if item in self.args:
            return self.args[item]
        else:
            return None
