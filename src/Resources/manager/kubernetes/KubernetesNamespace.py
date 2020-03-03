from kubernetes import client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException


class KubernetesNamespace(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = core_v1_api.CoreV1Api()

    def create(self, lab):
        namespace_definition = client.V1Namespace(metadata=client.V1ObjectMeta(name=lab.folder_hash,
                                                                               labels={'app': 'kathara'}
                                                                               )
                                                  )

        try:
            self.client.create_namespace(namespace_definition)
        except ApiException:
            return

    def undeploy(self, lab_hash=None):
        try:
            self.client.delete_namespace(lab_hash)
        except ApiException:
            return

    def wipe(self):
        namespaces = self.get_all()

        for namespace in namespaces:
            self.client.delete_namespace(namespace.metadata.name)

    def get_all(self):
        return self.client.list_namespace(label_selector="app=kathara").items
