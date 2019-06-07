from kubernetes import client
from kubernetes.client.apis import core_v1_api


def deploy_namespace(namespace_name):
    core_api = core_v1_api.CoreV1Api()

    core_api.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace_name)))


def delete(namespace_name):
    core_api = core_v1_api.CoreV1Api()

    core_api.delete_namespace(namespace_name)
