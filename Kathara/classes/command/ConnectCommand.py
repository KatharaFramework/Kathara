import docker
import sys
import io

from classes.command.Command import Command

import classes.trdparty.dockerpty as dockerpty

class ConnectCommand(Command):
    __slots__ = ['client']

    def __init__(self):
        Command.__init__(self)

        self.client = docker.from_env()

    def run(self, current_path, argv):

        container = self.client.containers.get("kathara_lollo_as1r1")

        dockerpty.exec_command(self.client, "kathara_lollo_as1r1", "/bin/bash")
