import base64

from kubernetes import client
from kubernetes.client.apis import core_v1_api


class KubernetesConfigMap(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = core_v1_api.CoreV1Api()

    def deploy_for_machine(self, machine):
        config_map = self._build_for_machine(machine)

        if config_map is None:
            return None

        return self.client.create_namespaced_config_map(body=config_map, namespace=machine.lab.folder_hash)

    def delete_for_machine(self, machine_name, machine_namespace):
        self.client.delete_namespaced_config_map(name=self._build_name_for_machine(machine_name, machine_namespace),
                                                 namespace=machine_namespace
                                                 )

    def _build_for_machine(self, machine):
        tar_data = machine.pack_data()

        # Create a ConfigMap on the cluster containing the base64 of the .tar.gz file
        # This will be decoded and extracted in the postStart hook of the pod
        if tar_data:
            data = {"hostlab.b64": base64.b64encode(tar_data).decode('utf-8')}
            metadata = client.V1ObjectMeta(name=self._build_name_for_machine(machine.name, machine.lab.folder_hash),
                                           deletion_grace_period_seconds=0
                                           )

            config_map = client.V1ConfigMap(api_version="v1",
                                            kind="ConfigMap",
                                            data=data,
                                            metadata=metadata
                                            )

            return config_map

        return None

    @staticmethod
    def _build_name_for_machine(machine_name, machine_namespace):
        return "%s-%s-files" % (machine_name, machine_namespace)
