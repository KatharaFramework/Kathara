from ..foundation.manager.IManager import IManager
from ..foundation.manager.ManagerFactory import ManagerFactory
from ..setting.Setting import Setting, POSSIBLE_MANAGERS


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
            manager_type = Setting.get_instance().manager_type

            self.manager = ManagerFactory().create_instance(module_args=(manager_type, ),
                                                            class_args=(manager_type.capitalize(), )
                                                            )

            ManagerProxy.__instance = self

    def deploy_lab(self, lab, privileged_mode=False):
        self.manager.deploy_lab(lab, privileged_mode)

    def update_lab(self, lab_diff):
        self.manager.update_lab(lab_diff)

    def undeploy_lab(self, lab_hash, selected_machines=None):
        self.manager.undeploy_lab(lab_hash, selected_machines)

    def wipe(self, all_users=False):
        self.manager.wipe(all_users)

    def connect_tty(self, lab_hash, machine_name, shell=None, logs=False):
        self.manager.connect_tty(lab_hash, machine_name, shell, logs)

    def exec(self, lab_hash, machine_name, command):
        return self.manager.exec(lab_hash, machine_name, command)

    def copy_files(self, machine, path, tar_data):
        self.manager.copy_files(machine, path, tar_data)

    def get_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        return self.manager.get_lab_info(lab_hash, machine_name, all_users)

    def get_machine_info(self, machine_name, lab_hash=None, all_users=False):
        return self.manager.get_machine_info(machine_name, lab_hash, all_users)

    def check_image(self, image_name):
        self.manager.check_image(image_name)

    def get_release_version(self):
        return self.manager.get_release_version()

    def get_formatted_manager_name(self):
        return self.manager.get_formatted_manager_name()

    @staticmethod
    def get_available_managers_name():
        managers = {}
        manager_factory = ManagerFactory()

        for manager_name in POSSIBLE_MANAGERS:
            manager = manager_factory.get_class(module_args=(manager_name, ),
                                                class_args=(manager_name.capitalize(), )
                                                )

            managers[manager_name] = manager.get_formatted_manager_name()

        return managers
