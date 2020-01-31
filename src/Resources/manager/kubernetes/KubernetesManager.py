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
        raise NotSupportedError("vconfig and lconfig not supported on Kubernetes.")

    @privileged
    def wipe(self, all_users=False):
        if all_users:
            raise NotSupportedError("--all flag not supported on Kubernetes.")

        self.k8s_machine.wipe()
        self.k8s_link.wipe()

    def get_manager_name(self):
        return "kubernetes"

    def get_formatted_manager_name(self):
        return "Kubernetes (Megalos)"
