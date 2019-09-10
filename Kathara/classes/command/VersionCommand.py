from classes.command.Command import Command


class VersionCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

    def run(self, argv):
        print('Current version: 0.1')
