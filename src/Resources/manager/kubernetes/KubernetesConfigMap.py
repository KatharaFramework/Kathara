import base64

from kubernetes import client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException


class KubernetesConfigMap(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = core_v1_api.CoreV1Api()

    def deploy_for_machine(self, machine):
        config_map = self._build_for_machine(machine)

        if config_map is None:
            return None

        return self.client.create_namespaced_config_map(body=config_map, namespace=machine.lab.folder_hash)

    @staticmethod
    def _build_for_machine(machine):
        tar_data = machine.pack_data()

        # Create a ConfigMap on the cluster containing the base64 of the .tar.gz file
        # This will be decoded and extracted in the postStart hook of the pod
        if tar_data:
            data = {"hostlab.b64": base64.b64encode(tar_data)}
            metadata = client.V1ObjectMeta(name="%s-%s-files" % (machine.name, machine.lab.folder_hash),
                                           deletion_grace_period_seconds=0
                                           )

            config_map = client.V1ConfigMap(api_version="v1",
                                            kind="ConfigMap",
                                            data=data,
                                            metadata=metadata
                                            )

            return config_map

        return None
