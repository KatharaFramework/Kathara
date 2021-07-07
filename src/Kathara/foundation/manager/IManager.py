import io
from abc import ABC, abstractmethod

from typing import Dict, Set

from Kathara.model import Machine

from Kathara.model.Lab import Lab


class IManager(ABC):
    @abstractmethod
    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None):
        raise NotImplementedError("You must implement `deploy_lab` method.")

    @abstractmethod
    def update_lab(self, lab_diff: Lab):
        raise NotImplementedError("You must implement `update_lab` method.")

    @abstractmethod
    def undeploy_lab(self, lab_hash: str, selected_machines: Set[str] = None):
        raise NotImplementedError("You must implement `undeploy_lab` method.")

    @abstractmethod
    def wipe(self, all_users: bool = False):
        raise NotImplementedError("You must implement `wipe` method.")

    @abstractmethod
    def connect_tty(self, lab_hash: str, machine_name: str, shell: str = None, logs: bool = False):
        raise NotImplementedError("You must implement `connect_tty` method.")

    @abstractmethod
    def exec(self, lab_hash: str, machine_name: str, command: str):
        raise NotImplementedError("You must implement `exec` method.")

    @abstractmethod
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]):
        raise NotImplementedError("You must implement `copy_files` method.")

    @abstractmethod
    def get_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False):
        raise NotImplementedError("You must implement `get_lab_info` method.")

    @abstractmethod
    def get_formatted_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False):
        raise NotImplementedError("You must implement `get_formatted_lab_info` method.")

    @abstractmethod
    def get_machine_api_object(self, lab_hash: str, machine_name: str):
        raise NotImplementedError("You must implement `get_machine_api_object` method.")

    @abstractmethod
    def get_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False):
        raise NotImplementedError("You must implement `get_machine_info` method.")

    @abstractmethod
    def get_formatted_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False):
        raise NotImplementedError("You must implement `get_formatted_machine_info` method.")

    @abstractmethod
    def check_image(self, image_name: str):
        raise NotImplementedError("You must implement `check_image` method.")

    @abstractmethod
    def get_release_version(self):
        raise NotImplementedError("You must implement `get_release_version` method.")

    @staticmethod
    def get_formatted_manager_name():
        raise NotImplementedError("You must implement `get_formatted_manager_name` method.")
