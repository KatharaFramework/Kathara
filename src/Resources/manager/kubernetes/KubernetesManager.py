from .KubernetesConfig import KubernetesConfig
from .KubernetesLink import KubernetesLink
from .KubernetesMachine import KubernetesMachine
from .KubernetesNamespace import KubernetesNamespace
from ...decorators import privileged
from ...exceptions import NotSupportedError
from ...foundation.manager.IManager import IManager


class KubernetesManager(IManager):
    __slots__ = ['client', 'k8s_namespace', 'k8s_link', 'k8s_machine']

    # @check_k8s_status
    def __init__(self):
        KubernetesConfig.load_kube_config()

        self.k8s_namespace = KubernetesNamespace()
        self.k8s_link = KubernetesLink()
        self.k8s_machine = KubernetesMachine()

    def deploy_lab(self, lab, privileged_mode=False):
        self.k8s_namespace.create(lab)

        self.k8s_link.deploy_links(lab)

        # TODO: Scheduler

        self.k8s_machine.deploy_machines(lab, privileged_mode)

    @privileged
    def update_lab(self, lab_diff):
        raise NotSupportedError("Not supported on Kubernetes.")

    @privileged
    def undeploy_lab(self, lab_hash, selected_machines=None):
        pass

    @privileged
    def wipe(self, all_users=False):
        if all_users:
            raise NotSupportedError("--all flag not supported on Kubernetes.")

        self.k8s_machine.wipe()
        self.k8s_link.wipe()

    @privileged
    def connect_tty(self, lab_hash, machine_name, shell, logs=False):
        pass

    @privileged
    def exec(self, machine, command):
        pass

    @privileged
    def copy_files(self, machine, path, tar_data):
        pass

    @privileged
    def get_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        pass

    @privileged
    def get_machine_info(self, machine_name, lab_hash=None, all_users=False):
        pass

    @privileged
    def check_image(self, image_name):
        pass

    @privileged
    def check_updates(self, settings):
        pass

    @privileged
    def get_release_version(self):
        pass

    @staticmethod
    def get_manager_name():
        return "kubernetes"

    @staticmethod
    def get_formatted_manager_name():
        return "Kubernetes (Megalos)"
