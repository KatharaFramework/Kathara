import base64
from typing import Optional

from kubernetes import client
from kubernetes.client.api import core_v1_api

from ...model.Machine import Machine
from ...utils import human_readable_bytes

MAX_FILE_SIZE = 3145728


class KubernetesConfigMap(object):
    """Class responsible for interacting with Kubernetes ConfigMap."""
    __slots__ = ['client']

    def __init__(self) -> None:
        self.client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

    def deploy_for_machine(self, machine: Machine) -> Optional[client.V1ConfigMap]:
        """Deploy and return a Kubernetes ConfigMap for the machine.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.

        Returns:
            Optional[client.V1ConfigMap]: A Kubernetes ConfigMap.
        """
        config_map = self._build_for_machine(machine)

        if config_map is None:
            return None

        return self.client.create_namespaced_config_map(body=config_map, namespace=machine.lab.hash)

    def delete_for_machine(self, machine_name: str, machine_namespace: str) -> None:
        """Delete the Kubernetes ConfigMap associated with the device.

        Args:
            machine_name (str): The name of a Kathara device.
            machine_namespace (str): the name of the namespace the device belongs to.

        Returns:
            None
        """
        self.client.delete_namespaced_config_map(name=self.build_name_for_machine(machine_name, machine_namespace),
                                                 namespace=machine_namespace
                                                 )

    @staticmethod
    def build_name_for_machine(machine_name: str, machine_namespace: str) -> str:
        """Return the name for the Kubernetes deployment.

        Args:
            machine_name (str): The name of a Kathara device.
            machine_namespace (str): the name of the namespace the device belongs to.

        Returns:
            str: The name for the ConfigMap in the format '|machine_name|-|machine_namespace|-files'.
        """
        return "%s-%s-files" % (machine_name, machine_namespace)

    def _build_for_machine(self, machine: Machine) -> Optional[client.V1ConfigMap]:
        """Build and return a Kubernetes ConfigMap for the device.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.

        Returns:
            Optional[client.V1ConfigMap]: The Kubernetes ConfigMap for the device.
        """
        tar_data = machine.pack_data()

        # Create a ConfigMap on the cluster containing the base64 of the .tar.gz file
        # This will be decoded and extracted in the postStart hook of the pod
        if tar_data:
            # Before creating the .tar.gz file, check if it is bigger than the maximum allowed size.
            tar_data_size = len(tar_data)
            if tar_data_size > MAX_FILE_SIZE:
                raise Exception(
                    'Unable to upload device folder. Maximum supported size: %s. Current: %s.' % (
                        human_readable_bytes(MAX_FILE_SIZE),
                        human_readable_bytes(tar_data_size)
                    )
                )

            data = {"hostlab.b64": base64.b64encode(tar_data).decode('utf-8')}
            metadata = client.V1ObjectMeta(name=self.build_name_for_machine(machine.meta['real_name'],
                                                                            machine.lab.hash),
                                           deletion_grace_period_seconds=0
                                           )

            config_map = client.V1ConfigMap(api_version="v1",
                                            kind="ConfigMap",
                                            data=data,
                                            metadata=metadata
                                            )

            return config_map

        return None
