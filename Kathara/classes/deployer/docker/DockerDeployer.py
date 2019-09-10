from classes.deployer.docker.DockerMachineDeployer import DockerMachineDeployer
from classes.deployer.docker.DockerLinkDeployer import DockerLinkDeployer
from classes.deployer.IDeployer import IDeployer


class DockerDeployer(IDeployer):
    __slots__ = ['machine_deployer', 'link_deployer']

    def __init__(self):
        self.machine_deployer = DockerMachineDeployer()
        self.link_deployer = DockerLinkDeployer()

    def deploy_lab(self, lab):
        for (_, link) in lab.links.items():
            self.link_deployer.deploy(link)

        for (_, machine) in lab.machines.items():
            self.machine_deployer.deploy(machine)

    def undeploy_lab(self, lab_hash):
        self.machine_deployer.undeploy(lab_hash)
        self.link_deployer.undeploy(lab_hash)

    def wipe(self):
        self.machine_deployer.wipe()
        self.link_deployer.wipe()
