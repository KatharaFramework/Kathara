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

        other_commands = []
        other_commands.append("sysctl net.ipv4.conf.all.rp_filter=0")
        other_commands.append("sysctl net.ipv4.conf.default.rp_filter=0")
        other_commands.append("sysctl net.ipv4.conf.lo.rp_filter=0")
        for (iface_num, machine_link) in machine.interfaces.items():
            machine_link.network_object.connect(machine_container)
            other_commands.append("sysctl net.ipv4.conf.eth%d.rp_filter=0" % iface_num)

        if "bridged" in machine.meta:
            bridged_network = self.client.networks.list(names="bridge").pop()
            bridged_network.connect(machine_container)

        # Ordine delle cose da eseguire: rp_filter, shared.startup, machine.startup e infine startup_commands
        if machine.lab.shared_startup_path:
          other_commands.append("/bin/bash /hostlab/shared.startup")

        if machine.startup_path:
          other_commands.append("/bin/bash /hostlab/%s.startup" % machine.name)

        start_commands = other_commands + machine.startup_commands

        print(start_commands)

        if machine.startup_commands:
            machine_container.exec_run(cmd=start_commands,
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
        return "%s_%s_%s" % (Setting.get_instance().machine_prefix, os.getlogin(), name)
