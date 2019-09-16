from abc import ABC, abstractmethod


class IDeployer(ABC):
    @abstractmethod
    def deploy_lab(self, lab, terminals, options, xterm):
        pass

    @abstractmethod
    def undeploy_lab(self, lab_hash):
        pass

    @abstractmethod
    def wipe(self):
        pass

    @abstractmethod
    def connect_tty(self, lab_hash, machine_name, command):
        pass

    @abstractmethod
    def get_info_stream(self, lab_hash):
        pass
