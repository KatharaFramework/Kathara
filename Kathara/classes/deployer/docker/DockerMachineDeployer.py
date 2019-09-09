import os

import docker

# TODO: Remove
IMAGE_HUB = 'kathara'


class DockerMachineDeployer(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = docker.from_env()

    def deploy(self, machine):
        image = machine.meta["image"] if "image" in machine.meta else ("%s/%s" % (IMAGE_HUB, "netkit_base"))

        machine_container = self.client.containers.create(image=image,
                                                          name=self._get_container_name(machine.name),
                                                          hostname=machine.name,
                                                          privileged=True,
                                                          network_mode=None,
                                                          tty=True,
                                                          stdin_open=True,
                                                          detach=True,
                                                          )

        machine_container.start()

    # noinspection PyMethodMayBeStatic
    def _get_container_name(self, name):
        return "kathara_%s_%s" % (os.getlogin(), name)
