import io
from typing import Set, Dict

from Kathara.model.Machine import Machine

from ..foundation.manager.IManager import IManager
from ..foundation.manager.ManagerFactory import ManagerFactory
from ..setting.Setting import Setting, AVAILABLE_MANAGERS
from src.Kathara.model.Lab import Lab


class Kathara(IManager):
    __slots__ = ['manager']

    __instance = None

    @staticmethod
    def get_instance():
        if Kathara.__instance is None:
            Kathara()

        return Kathara.__instance

    def __init__(self):
        if Kathara.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            manager_type = Setting.get_instance().manager_type

            self.manager = ManagerFactory().create_instance(module_args=(manager_type,),
                                                            class_args=(manager_type.capitalize(),)
                                                            )

            Kathara.__instance = self

    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None):
        self.manager.deploy_lab(lab, selected_machines)

    def update_lab(self, lab_diff: Lab):

        self.manager.update_lab(lab_diff)

    def undeploy_lab(self, lab_hash: str, selected_machines: Set[str] = None):
        self.manager.undeploy_lab(lab_hash, selected_machines)

    def wipe(self, all_users: bool = False):
        self.manager.wipe(all_users)

    def connect_tty(self, lab_hash: str, machine_name: str, shell: str = None, logs: bool = False):
        self.manager.connect_tty(lab_hash, machine_name, shell, logs)

    def exec(self, lab_hash: str, machine_name: str, command: str):
        return self.manager.exec(lab_hash, machine_name, command)

    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]):
        self.manager.copy_files(machine, guest_to_host)

    def get_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False):
        return self.manager.get_lab_info(lab_hash, machine_name, all_users)

    def get_formatted_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False):
        return self.manager.get_formatted_lab_info(lab_hash, machine_name, all_users)

    def get_machine_api_object(self, lab_hash: str, machine_name: str):
        return self.manager.get_machine_api_object(lab_hash, machine_name)

    def get_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False):
        return self.manager.get_machine_info(machine_name, lab_hash, all_users)

    def get_formatted_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False):
        return self.manager.get_formatted_machine_info(machine_name, lab_hash, all_users)

    def check_image(self, image_name: str):
        self.manager.check_image(image_name)

    def get_release_version(self):
        return self.manager.get_release_version()

    def get_formatted_manager_name(self):
        return self.manager.get_formatted_manager_name()

    @staticmethod
    def get_available_managers_name():
        managers = {}
        manager_factory = ManagerFactory()

        for manager_name in AVAILABLE_MANAGERS:
            manager = manager_factory.get_class(module_args=(manager_name,),
                                                class_args=(manager_name.capitalize(),)
                                                )

            managers[manager_name] = manager.get_formatted_manager_name()

        return managers
