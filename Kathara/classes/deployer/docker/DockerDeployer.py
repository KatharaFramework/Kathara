import docker

from .DockerLinkDeployer import DockerLinkDeployer
from .DockerMachineDeployer import DockerMachineDeployer
from ..IDeployer import IDeployer
from ...model.Link import BRIDGE_LINK_NAME

import os



class DockerDeployer(IDeployer):
    __slots__ = ['machine_deployer', 'link_deployer', 'client']

    def __init__(self):
        self.client = docker.from_env()

        self.machine_deployer = DockerMachineDeployer(self.client)
        self.link_deployer = DockerLinkDeployer(self.client)

    # TODO: Decorator to check if Docker is running
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

    # TODO: Decorator to check if Docker is running
    def undeploy_lab(self, lab_hash):
        self.machine_deployer.undeploy(lab_hash)
        self.link_deployer.undeploy(lab_hash)

    # TODO: Decorator to check if Docker is running
    def wipe(self):
        self.machine_deployer.wipe()
        self.link_deployer.wipe()

    # TODO: Decorator to check if Docker is running
    def connect_tty(self, lab_hash, machine_name, command):
        self.machine_deployer.connect(lab_hash=lab_hash,
                                      machine_name=machine_name,
                                      command=command
                                      )

    # TODO: Decorator to check if Docker is running
    def get_info_stream(self, lab_hash):
        machines = self.machine_deployer.get_machines_by_filters(lab_hash=lab_hash)

        while True:
            for machine in machines:
                machine_stream = machine.stats(stream=True, decode=True)
                result = next(machine_stream)

                print(machine.name + " " + result["read"])

            # os.system('cls')  # For Windows
            os.system('clear')  # For Linux/OS X