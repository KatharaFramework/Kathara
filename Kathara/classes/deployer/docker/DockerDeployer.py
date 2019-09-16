from subprocess import Popen

import docker

import utils
from .DockerLinkDeployer import DockerLinkDeployer
from .DockerMachineDeployer import DockerMachineDeployer
from ..IDeployer import IDeployer
from ...model.Link import BRIDGE_LINK_NAME
from ...setting.Setting import Setting


class DockerDeployer(IDeployer):
    __slots__ = ['machine_deployer', 'link_deployer', 'client']

    def __init__(self):
        self.client = docker.from_env()
        self.machine_deployer = DockerMachineDeployer(self.client)
        self.link_deployer = DockerLinkDeployer(self.client)

    def deploy_lab(self, lab, terminals, options, xterm):
        # Deploy all lab links.
        for (_, link) in lab.links.items():
            self.link_deployer.deploy(link)

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.link_deployer.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.network_object = docker_bridge

        # Deploy all lab machines.
        for (_, machine) in lab.machines.items():
            self.machine_deployer.deploy(machine,
                                         terminals=terminals,
                                         options=options,
                                         xterm=xterm
                                         )

    def undeploy_lab(self, lab_hash):
        self.machine_deployer.undeploy(lab_hash)
        self.link_deployer.undeploy(lab_hash)

    def wipe(self):
        self.machine_deployer.wipe()
        self.link_deployer.wipe()

    def connect_tty(self, lab_hash, machine_name, command):
        container_name = DockerMachineDeployer.get_container_name(machine_name)

        containers = self.client.containers.list(all=True,
                                                 filters={"label": "lab_hash=%s" % lab_hash, "name": container_name}
                                                 )

        if len(containers) != 1:
            raise Exception("Error getting the machine `%s` inside the lab." % machine_name)
        else:
            container = containers[0]

        if not command:
            command = Setting.get_instance().machine_shell

        def linux_connect():
            from ...trdparty.dockerpty.pty import PseudoTerminal

            # Needed with low level api because we need the id of the exec_create
            resp = self.client.api.exec_create(container.id,
                                               command,
                                               stdout=True,
                                               stderr=True,
                                               stdin=True,
                                               tty=True,
                                               privileged=True
                                               )

            exec_output = self.client.api.exec_start(resp['Id'],
                                                     tty=True,
                                                     socket=True,
                                                     demux=True
                                                     )

            PseudoTerminal(self.client, exec_output, resp['Id']).start()

        def windows_connect():
            Popen(["docker", "exec", "-it", container.id, command])

        utils.exec_by_platform(linux_connect, windows_connect, linux_connect)
