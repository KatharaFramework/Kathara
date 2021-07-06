from abc import ABC, abstractmethod


class IManager(ABC):
    @abstractmethod
    def deploy_lab(self, lab, selected_machines=None):
        raise NotImplementedError("You must implement `deploy_lab` method.")

    @abstractmethod
    def update_lab(self, lab_diff):
        raise NotImplementedError("You must implement `update_lab` method.")

    @abstractmethod
    def undeploy_lab(self, lab_hash, selected_machines=None):
        raise NotImplementedError("You must implement `undeploy_lab` method.")

    @abstractmethod
    def wipe(self, all_users=False):
        raise NotImplementedError("You must implement `wipe` method.")

    @abstractmethod
    def connect_tty(self, lab_hash, machine_name, shell=None, logs=False):
        raise NotImplementedError("You must implement `connect_tty` method.")

    @abstractmethod
    def exec(self, lab_hash, machine_name, command):
        raise NotImplementedError("You must implement `exec` method.")

    @abstractmethod
    def copy_files(self, machine, guest_to_host):
        raise NotImplementedError("You must implement `copy_files` method.")

    @abstractmethod
    def get_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        raise NotImplementedError("You must implement `get_lab_info` method.")

    @abstractmethod
    def get_formatted_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        raise NotImplementedError("You must implement `get_formatted_lab_info` method.")

    @abstractmethod
    def get_machine_api_object(self, lab_hash, machine_name):
        raise NotImplementedError("You must implement `get_machine_api_object` method.")

    @abstractmethod
    def get_machine_info(self, machine_name, lab_hash=None, all_users=False):
        raise NotImplementedError("You must implement `get_machine_info` method.")

    @abstractmethod
    def get_formatted_machine_info(self, machine_name, lab_hash=None, all_users=False):
        raise NotImplementedError("You must implement `get_formatted_machine_info` method.")

    @abstractmethod
    def check_image(self, image_name):
        raise NotImplementedError("You must implement `check_image` method.")

    @abstractmethod
    def get_release_version(self):
        raise NotImplementedError("You must implement `get_release_version` method.")

    @staticmethod
    def get_formatted_manager_name():
        raise NotImplementedError("You must implement `get_formatted_manager_name` method.")
