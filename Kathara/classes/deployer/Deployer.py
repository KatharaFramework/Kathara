import utils
from .IDeployer import IDeployer

deployer_type = "docker"


class Deployer(IDeployer):
    __slots__ = ['deployer']

    __instance = None

    @staticmethod
    def get_instance():
        if Deployer.__instance is None:
            Deployer()

        return Deployer.__instance

    def __init__(self):
        if Deployer.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.deployer = utils.class_for_name("classes.deployer.%s" % deployer_type,
                                                 "%sDeployer" % deployer_type.capitalize()
                                                 )()

            Deployer.__instance = self

    def deploy_lab(self, lab, terminals, options, xterm):
        self.deployer.deploy_lab(lab, terminals, options, xterm)

    def undeploy_lab(self, lab_hash):
        self.deployer.undeploy_lab(lab_hash)

    def wipe(self):
        self.deployer.wipe()

    def connect_tty(self, lab_hash, machine_name, command):
        self.deployer.connect_tty(lab_hash, machine_name, command)
