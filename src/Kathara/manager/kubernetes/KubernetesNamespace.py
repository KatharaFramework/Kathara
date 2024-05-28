import logging
from typing import Optional, Iterable

from kubernetes import client, watch
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException

from .KubernetesSecret import KubernetesSecret, DOCKERCONFIGJSON_SECRET_NAME
from ...setting.Setting import Setting
from ...model.Lab import Lab


class KubernetesNamespace(object):
    """Class responsible for interacting with Kubernetes namespaces."""

    __slots__ = ['client', 'kubernetes_secret']

    def __init__(self, kubernetes_secret: KubernetesSecret) -> None:
        self.client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

        self.kubernetes_secret = kubernetes_secret

    def create(self, lab: Lab) -> Optional[client.V1Namespace]:
        """Return a Kubernetes namespace from a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.

        Returns:
            Optional[client.V1Namespace]: The Kubernetes namespace for the network scenario.
        """
        namespace_definition = client.V1Namespace(
            metadata=client.V1ObjectMeta(name=lab.hash, labels={'app': 'kathara'})
        )

        try:
            self.client.create_namespace(namespace_definition)
            self._wait_namespace_creation(lab.hash)
            docker_config_json = Setting.get_instance().docker_config_json
            if docker_config_json:
                self.kubernetes_secret.create_dockerconfigjson_secret(lab.hash, DOCKERCONFIGJSON_SECRET_NAME, docker_config_json)
        except ApiException:
            return None

    def undeploy(self, lab_hash: str = None) -> None:
        """Delete the Kubernetes namespace corresponding to the lab_hash.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.

        Returns:
            None
        """
        try:
            self.client.delete_namespace(lab_hash)
            self._wait_namespaces_deletion(label_selector=f"kubernetes.io/metadata.name={lab_hash}")
        except ApiException:
            return

    def wipe(self) -> None:
        """Delete all the Kathara Kubernetes namespaces.

        Returns:
            None
        """
        namespaces = self.get_all()

        for namespace in namespaces:
            self.client.delete_namespace(namespace.metadata.name)

        self.kubernetes_secret.wipe()

        self._wait_namespaces_deletion(label_selector="app=kathara")

    def get_all(self) -> Iterable[client.V1Namespace]:
        """Return an Iterable containing all the Kubernetes namespaces related to Kathara.

        Returns:
            Iterable[client.V1Namespace]: an Iterable containing all the Kubernetes namespaces related to Kathara.
        """
        return self.client.list_namespace(label_selector="app=kathara").items

    def get_namespace(self, lab_hash: str) -> Optional[client.V1Namespace]:
        """Return an Iterable containing all the Kubernetes namespaces related to Kathara.

        Returns:
            Iterable[client.V1Namespace]: an Iterable containing all the Kubernetes namespaces related to Kathara.
        """
        namespace = self.client.list_namespace(label_selector=f"kubernetes.io/metadata.name={lab_hash}").items
        return namespace.pop() if namespace else None

    def _wait_namespace_creation(self, lab_hash: str) -> None:
        """Wait the creation of the specified Kubernetes Namespace. Returns when the namespace becomes `Active`.

        Args:
            lab_hash (str): The name of the Kubernetes Namespace to wait.

        Returns:
            None
        """
        w = watch.Watch()
        for event in w.stream(self.client.list_namespace,
                              label_selector=f"kubernetes.io/metadata.name={lab_hash}"):
            logging.debug(f"Event: {event['type']} - Namespace: {event['object'].metadata.name}")

            if event['object'].status.phase == 'Active':
                w.stop()

    def _wait_namespaces_deletion(self, label_selector: str) -> None:
        """Wait the deletion of the specified Kubernetes Namespaces. Return when specified namespaces are terminated.

        Args:
            label_selector (str): The label used to select the namespaces.

        Returns:
            None
        """
        namespaces_to_delete = len(self.client.list_namespace(label_selector=label_selector).items)

        if namespaces_to_delete > 0:
            w = watch.Watch()
            deleted_namespaces = 0
            for event in w.stream(self.client.list_namespace, label_selector=label_selector):
                logging.debug(f"Event: {event['type']} - Namespace: {event['object'].metadata.name}")

                if event['type'] == "DELETED":
                    deleted_namespaces += 1

                if deleted_namespaces == namespaces_to_delete:
                    w.stop()
