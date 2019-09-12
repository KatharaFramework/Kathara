import docker
import sys
import select
import io

from classes.command.Command import Command
from classes.trdparty.dockerpty import dockerpty

class ConnectCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        self.client = docker.from_env()

    def run(self, current_path, argv):
        container = self.client.containers.get("kathara_loren_as1r1")

        dockerpty.exec_command(self.client, "kathara_loren_as1r1", "/bin/bash")
