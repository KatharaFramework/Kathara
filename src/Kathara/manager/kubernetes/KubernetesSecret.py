import logging
from typing import Optional, Iterable

from kubernetes import client, watch
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException

from ...setting.Setting import Setting
from ...model.Lab import Lab

DOCKERCONFIGJSON_SECRET_NAME = 'private-registry'

class KubernetesSecret(object):
    """Class responsible for interacting with Kubernetes secrets."""

    __slots__ = ['client']

    def __init__(self) -> None:
        self.client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

    def create_dockerconfigjson_secret(self, lab_hash: str, name: str,
                                       docker_config_json: str) -> Optional[client.V1Secret]:
        """Return a Kubernetes secret of type kubernetes.io/dockerconfigjson from a Kathara network scenario.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.
            name (str): The name of the secret.
            docker_config_json (str): A Docker configuration JSON.

        Returns:
            Optional[client.V1Secret]: The Kubernetes secret for the Docker configuration JSON.
        """
        secret_definition = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, namespace=lab_hash, labels={'app': 'kathara'}),
            type="kubernetes.io/dockerconfigjson",
            data={".dockerconfigjson": docker_config_json}
        )

        try:
            self.client.create_namespaced_secret(lab_hash, secret_definition)
            self._wait_secret_creation(lab_hash, name)
        except ApiException:
            return None

    def delete(self, lab_hash: str, name: str) -> None:
        """Delete the Kubernetes secret corresponding to the lab_hash.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.
            name (str): The name of the secret.

        Returns:
            None
        """
        try:
            self.client.delete_namespaced_secret(name, lab_hash)
            self._wait_secrets_deletion(lab_hash, field_selector=f"metadata.name={name}")
        except ApiException:
            return

    def wipe(self) -> None:
        """Namespace deletion implies automatic deletion of all secrets.

        Returns:
            None
        """
        pass

    def _wait_secret_creation(self, lab_hash: str, name: str) -> None:
        """Wait for the secret creation to be completed.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.
            name (str): The name of the secret.

        Returns:
            None
        """
        w = watch.Watch()
        for event in w.stream(self.client.list_namespaced_secret, namespace=lab_hash, field_selector=f"metadata.name={name}"):
            logging.debug(f"Event: {event['type']} - Secret: {event['object'].metadata.name}")

            if event['type'] == "ADDED":
                break

    def _wait_secrets_deletion(self, lab_hash: str, field_selector: str = None) -> None:
        """Wait the deletion of the specified Kubernetes secrets. Returns when the secrets are deleted.

        Args:
            lab_hash (str): The hash of a Kathara network scenario.
            field_selector (str): The field selector for the secret.

        Returns:
            None
        """
        secrets_to_delete = len(self.client.list_namespaced_secret(lab_hash, field_selector=field_selector).items)

        if secrets_to_delete > 0:
            w = watch.Watch()
            deleted_secrets = 0
            for event in w.stream(self.client.list_namespaced_secret, namespace=lab_hash, field_selector=field_selector):
                logging.debug(f"Event: {event['type']} - Secret: {event['object'].metadata.name}")

                if event['type'] == "DELETED":
                    deleted_secrets += 1

                if deleted_secrets == secrets_to_delete:
                    w.stop()
