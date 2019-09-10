import os

import docker

from classes.setting.Setting import Setting


class DockerMachineDeployer(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = docker.from_env()

    def deploy(self, machine):
        image = machine.meta["image"] if "image" in machine.meta else Setting.get_instance().image
        memory = machine.meta["mem"] if 'mem' in machine.meta else None

        ports = None
        if "port" in machine.meta:
            try:
                ports = {'3000/tcp': int(machine.meta["port"])}
            except ValueError:
                pass

        machine_container = self.client.containers.create(image=image,
                                                          name=self._get_container_name(machine.name),
                                                          hostname=machine.name,
                                                          privileged=True,
                                                          network_mode=None,
                                                          mem_limit=memory,
                                                          ports=ports,
                                                          tty=True,
                                                          stdin_open=True,
                                                          detach=True,
                                                          labels={"lab_hash": machine.lab.folder_hash, "app": "kathara"}
                                                          )

        for (_, machine_link) in machine.interfaces.items():
            machine_link.network_object.connect(machine_container)

        if "bridged" in machine.meta:
            bridged_network = self.client.networks.list(names="bridge").pop()
            bridged_network.connect(machine_container)

        if machine.startup_commands:
            machine_container.exec_run(cmd=machine.startup_commands,
                                       stdout=False,
                                       stderr=False,
                                       privileged=True,
                                       detach=True
                                       )

        return machine_container

    def undeploy(self, lab_hash):
        containers = self.client.containers.list(all=True, filters={"label": "lab_hash=%s" % lab_hash})

        for container in containers:
            container.remove(force=True)

    def wipe(self):
        containers = self.client.containers.list(all=True, filters={"label": "app=kathara"})

        for container in containers:
            container.remove(force=True)

    # noinspection PyMethodMayBeStatic
    def _get_container_name(self, name):
        return "kathara_%s_%s" % (os.getlogin(), name)
