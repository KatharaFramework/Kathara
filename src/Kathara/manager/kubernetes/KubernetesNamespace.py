from typing import Optional, Iterable

from kubernetes import client
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException

from ...model.Lab import Lab


class KubernetesNamespace(object):
    __slots__ = ['client']

    def __init__(self) -> None:
        self.client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

    def create(self, lab: Lab) -> Optional[client.V1Namespace]:
        namespace_definition = client.V1Namespace(metadata=client.V1ObjectMeta(name=lab.hash,
                                                                               labels={'app': 'kathara'}
                                                                               )
                                                  )

        try:
            self.client.create_namespace(namespace_definition)
        except ApiException:
            return None

    def undeploy(self, lab_hash: str = None) -> None:
        try:
            self.client.delete_namespace(lab_hash)
        except ApiException:
            return

    def wipe(self) -> None:
        namespaces = self.get_all()

        for namespace in namespaces:
            self.client.delete_namespace(namespace.metadata.name)

    def get_all(self) -> Iterable[client.V1Namespace]:
        return self.client.list_namespace(label_selector="app=kathara").items
