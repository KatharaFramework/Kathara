from abc import ABC, abstractmethod


class IManager(ABC):
    @abstractmethod
    def deploy_lab(self, lab, options=None):
        pass

    @abstractmethod
    def undeploy_lab(self, lab_hash, selected_machines):
        pass

    @abstractmethod
    def wipe(self):
        pass

    @abstractmethod
    def connect_tty(self, lab_hash, machine_name, shell):
        pass

    @abstractmethod
    def get_lab_info(self, lab_hash=None):
        pass

    @abstractmethod
    def get_machine_info(self, machine_name):
        pass

    @abstractmethod
    def get_version(self):
        pass
