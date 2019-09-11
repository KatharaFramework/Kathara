import utils
from classes.deployer.IDeployer import IDeployer

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

    # noinspection PyMethodMayBeStatic
    def deploy_lab(self, lab):
        self.deployer.deploy_lab(lab)

    # noinspection PyMethodMayBeStatic
    def undeploy_lab(self, lab_hash):
        self.deployer.undeploy_lab(lab_hash)

    def wipe(self):
        self.deployer.wipe()
