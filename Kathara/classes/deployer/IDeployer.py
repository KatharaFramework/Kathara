from abc import ABC, abstractmethod


class IDeployer(ABC):
    @abstractmethod
    def deploy_lab(self, lab):
        pass

    @abstractmethod
    def undeploy_lab(self, lab_hash):
        pass

    @abstractmethod
    def wipe(self):
        pass

    @abstractmethod
    def ConnectTTY(self, lab_hash, machine_name, command):
        pass
