import utils
from ..foundation.adapter.IAdapter import IAdapter
from ..setting.Setting import Setting


class Controller(IAdapter):
    __slots__ = ['adapter']

    __instance = None

    @staticmethod
    def get_instance():
        if Controller.__instance is None:
            Controller()

        return Controller.__instance

    def __init__(self):
        if Controller.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            deployer_type = Setting.get_instance().deployer_type

            self.adapter = utils.class_for_name("classes.adapter.%s" % deployer_type,
                                                 "%sAdapter" % deployer_type.capitalize()
                                                )()

            Controller.__instance = self

    def deploy_lab(self, lab, options):
        self.adapter.deploy_lab(lab, options)

    def undeploy_lab(self, lab_hash, selected_machines):
        self.adapter.undeploy_lab(lab_hash, selected_machines)

    def wipe(self):
        self.adapter.wipe()

    def connect_tty(self, lab_hash, machine_name, shell):
        self.adapter.connect_tty(lab_hash, machine_name, shell)

    def get_info_stream(self, lab_hash):
        self.adapter.get_info_stream(lab_hash)
