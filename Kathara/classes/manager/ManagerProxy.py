import utils
from ..foundation.manager.IManager import IManager
from ..setting.Setting import Setting


class ManagerProxy(IManager):
    __slots__ = ['manager']

    __instance = None

    @staticmethod
    def get_instance():
        if ManagerProxy.__instance is None:
            ManagerProxy()

        return ManagerProxy.__instance

    def __init__(self):
        if ManagerProxy.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            deployer_type = Setting.get_instance().deployer_type

            self.manager = utils.class_for_name("classes.manager.%s" % deployer_type,
                                                 "%sManager" % deployer_type.capitalize()
                                                )()

            ManagerProxy.__instance = self

    def deploy_lab(self, lab):
        self.manager.deploy_lab(lab)

    def update_lab(self, lab_diff):
        self.manager.update_lab(lab_diff)

    def undeploy_lab(self, lab_hash, selected_machines=None):
        self.manager.undeploy_lab(lab_hash, selected_machines)

    def wipe(self):
        self.manager.wipe()

    def connect_tty(self, lab_hash, machine_name, shell):
        self.manager.connect_tty(lab_hash, machine_name, shell)

    def get_lab_info(self, lab_hash=None, machine_name=None):
        return self.manager.get_lab_info(lab_hash, machine_name)

    def get_machine_info(self, machine_name, lab_hash=None):
        return self.manager.get_machine_info(machine_name, lab_hash)

    def check_image(self, image_name):
        self.manager.check_image(image_name)

    def check_updates(self, settings):
        self.manager.check_updates(settings)

    def get_release_version(self):
        return self.manager.get_release_version()
