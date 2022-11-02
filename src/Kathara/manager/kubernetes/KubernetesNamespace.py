import logging
from typing import Optional, Iterable

from kubernetes import client, watch
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException

from ...model.Lab import Lab


class KubernetesNamespace(object):
    """Class responsible for interacting with Kubernetes namespaces."""

    __slots__ = ['client']

    def __init__(self) -> None:
        self.client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

    def create(self, lab: Lab) -> Optional[client.V1Namespace]:
        """Return a Kubernetes namespace from a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.

        Returns:
            Optional[client.V1Namespace]: The Kubernetes namespace for the network scenario.
        """
        namespace_definition = client.V1Namespace(metadata=client.V1ObjectMeta(name=lab.hash,
                                                                               labels={'app': 'kathara'}
                                                                               )
                                                  )

        try:
            self.client.create_namespace(namespace_definition)
            self._wait_namespace_creation(lab.hash)
        except ApiException:
            return None

    def _wait_namespace_creation(self, lab_hash):
        w = watch.Watch()
        for event in w.stream(self.client.list_namespace,
                              label_selector=f"kubernetes.io/metadata.name={lab_hash}"):
            logging.debug(f"Event: {event['type']} namespace {event['object'].metadata.name} for this network scenario")

            if event['object'].status.phase == 'Active':
                w.stop()

    def undeploy(self, lab_hash: str = None) -> None:
        """Delete the Kubernetes namespace corresponding to the lab_hash.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.

        Returns:
            None
        """
        try:
            self.client.delete_namespace(lab_hash)
            self._wait_namespace_deletion(lab_hash)
        except ApiException:
            return

    def _wait_namespace_deletion(self, lab_hash):
        w = watch.Watch()
        for event in w.stream(self.client.list_namespace,
                              label_selector=f"kubernetes.io/metadata.name={lab_hash}"):
            logging.debug(f"Event: {event['type']} namespace {event['object'].metadata.name} for this network scenario")

            if event['type'] == "DELETED":
                w.stop()

    def wipe(self) -> None:
        """Delete all the Kathara Kubernetes namespaces.

        Returns:
            None
        """
        namespaces = self.get_all()

        for namespace in namespaces:
            self.client.delete_namespace(namespace.metadata.name)

    def get_all(self) -> Iterable[client.V1Namespace]:
        """Return an Iterable containing all the Kubernetes namespaces relatively to Kathara.

        Returns:
            Iterable[client.V1Namespace]: an Iterable containing all the Kubernetes namespaces relatively to Kathara.
        """
        return self.client.list_namespace(label_selector="app=kathara").items

    def get_namespace(self, lab_hash: str) -> Optional[client.V1Namespace]:
        """Return an Iterable containing all the Kubernetes namespaces relatively to Kathara.

        Returns:
            Iterable[client.V1Namespace]: an Iterable containing all the Kubernetes namespaces relatively to Kathara.
        """
        namespace = self.client.list_namespace(label_selector=f"kubernetes.io/metadata.name={lab_hash}").items
        return namespace.pop() if namespace else None
