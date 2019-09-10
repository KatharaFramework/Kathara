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
                                                          labels={"lab_hash":str(machine.lab.folder_hash)}
                                                          )

        machine_container.start()

    def undeploy(self, lab_hash):
        containers = self.client.containers.list(filters= {"label":"lab_hash=%s" % lab_hash})
        
        for container in containers:
          container.remove(force=True)

    # noinspection PyMethodMayBeStatic
    def _get_container_name(self, name):
        return "kathara_%s_%s" % (os.getlogin(), name)
