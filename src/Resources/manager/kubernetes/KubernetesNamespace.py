from kubernetes import client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException

from ...exceptions import LabAlreadyExistsError


class KubernetesNamespace(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = core_v1_api.CoreV1Api()

    def create(self, lab):
        namespace_definition = client.V1Namespace(metadata=client.V1ObjectMeta(name=lab.folder_hash))

        try:
            self.client.create_namespace(namespace_definition)
        except ApiException:
            raise LabAlreadyExistsError("Lab is already deployed.")
