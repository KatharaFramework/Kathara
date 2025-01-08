import logging
from typing import Optional, Dict, List

from kubernetes import client, watch
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException

from ...model.Lab import Lab
from ...setting.Setting import Setting


class KubernetesSecret(object):
    """Class responsible for interacting with Kubernetes secrets."""
    __slots__ = ['client']

    def __init__(self) -> None:
        self.client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

    def create(self, lab: Lab) -> List[client.V1Secret]:
        """Create the Kubernetes secrets for a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.

        Returns:
            List[client.V1Secret]: A list of created Kubernetes secrets for the network scenario.
        """
        secrets = []

        docker_config_json = Setting.get_instance().docker_config_json
        if docker_config_json:
            secret = self._create_secret(
                lab.hash, "private-registry",
                "kubernetes.io/dockerconfigjson", {".dockerconfigjson": docker_config_json}
            )

            if secret:
                secrets.append(secret)

        return secrets

    def _create_secret(self, lab_hash: str, name: str, secret_type: str, data: Dict) -> Optional[client.V1Secret]:
        """Create a Kubernetes secret of a secret type for a Kathara network scenario.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.
            name (str): The name of the secret.
            secret_type (str): The type of the secret.
            data (Dict): A dictionary containing the data of the secret.

        Returns:
            Optional[client.V1Secret]: The Kubernetes secret.
        """
        secret_definition = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, namespace=lab_hash, labels={'app': 'kathara'}),
            type=secret_type,
            data=data
        )

        try:
            self.client.create_namespaced_secret(lab_hash, secret_definition)
            self._wait_secret_creation(lab_hash, name)

            return secret_definition
        except ApiException:
            return None

    def _wait_secret_creation(self, lab_hash: str, name: str) -> None:
        """Wait for the secret creation to be completed.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.
            name (str): The name of the secret.

        Returns:
            None
        """
        w = watch.Watch()
        for event in w.stream(self.client.list_namespaced_secret, namespace=lab_hash,
                              field_selector=f"metadata.name={name}"):
            logging.debug(f"Event: {event['type']} - Secret: {event['object'].metadata.name}")

            if event['type'] == "ADDED":
                break
