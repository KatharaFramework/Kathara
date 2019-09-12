import docker

from classes.deployer.IDeployer import IDeployer
from classes.deployer.docker.DockerLinkDeployer import DockerLinkDeployer
from classes.deployer.docker.DockerMachineDeployer import DockerMachineDeployer
from classes.trdparty.dockerpty.pty import PseudoTerminal
from classes.setting.Setting import Setting

class DockerDeployer(IDeployer):
    __slots__ = ['machine_deployer', 'link_deployer', 'client']

    def __init__(self):
        self.client = docker.from_env()
        self.machine_deployer = DockerMachineDeployer(self.client)
        self.link_deployer = DockerLinkDeployer(self.client)

    def deploy_lab(self, lab):
        for (_, link) in lab.links.items():
            self.link_deployer.deploy(link)

        docker_bridge = self.link_deployer.get_docker_bridge()
        link = lab.get_or_new_link("docker_bridge")
        link.network_object = docker_bridge

        for (_, machine) in lab.machines.items():
            self.machine_deployer.deploy(machine)

    def undeploy_lab(self, lab_hash):
        self.machine_deployer.undeploy(lab_hash)
        self.link_deployer.undeploy(lab_hash)

    def wipe(self):
        self.machine_deployer.wipe()
        self.link_deployer.wipe()

    def ConnectTTY(self, lab_hash, machine_name, command):

        container_name = DockerMachineDeployer._get_container_name(machine_name)

        containers = self.client.containers.list(all=True, filters={"label": "lab_hash=%s" % lab_hash, "name":container_name})

        if len(containers) != 1:
            raise Exception("Error getting the machine %s inside this lab" % machine_name)
        else:
            container = containers[0]

        if not command:
            command = Setting.get_instance().machine_shell

        # Needed with low level api because we need the id of the exec_create
        resp = self.client.api.exec_create(container.id, command, stdout=True, stderr=True, stdin=True, tty=True,privileged=True)
        exec_output = self.client.api.exec_start(resp['Id'], tty=True, socket=True, demux=True)

        PseudoTerminal(self.client, exec_output, resp['Id']).start()
