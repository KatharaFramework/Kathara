import utils

deployer_type = "docker"


class Deployer(object):
    __slots__ = []

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
            Deployer.__instance = self

    # noinspection PyMethodMayBeStatic
    def deploy(self, lab):
        machine_deployer = utils.class_for_name("classes.deployer.%s" % deployer_type,
                                                "%sMachineDeployer" % deployer_type.capitalize()
                                                )()

        link_deployer = utils.class_for_name("classes.deployer.%s" % deployer_type,
                                             "%sLinkDeployer" % deployer_type.capitalize()
                                             )()

        for (_, link) in lab.links.items():
            link_deployer.deploy(link)

        for (_, machine) in lab.machines.items():
            machine_deployer.deploy(machine)


    def undeploy(self, lab_hash):
        machine_deployer = utils.class_for_name("classes.deployer.%s" % deployer_type,
                                                "%sMachineDeployer" % deployer_type.capitalize()
                                                )()

        link_deployer = utils.class_for_name("classes.deployer.%s" % deployer_type,
                                             "%sLinkDeployer" % deployer_type.capitalize()
                                             )()

        machine_deployer.undeploy(lab_hash)
        # link_deployer.undeploy(lab_hash)

        
