import docker


class DockerLinkDeployer(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = docker.from_env()

    def deploy(self, machine):
        pass
