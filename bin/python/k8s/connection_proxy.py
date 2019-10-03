import sys
import time

import utils as u
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException

import k8s_utils


def get_pod_name_by_deployment_name(core_api, name, namespace):
    try:
        pods = core_api.list_namespaced_pod(namespace=namespace)        

        for pod in pods.items:
            if (name + "-") in pod.metadata.name:
                return pod.metadata.name
    except ApiException as e:
        sys.stderr.write("Error searching machine `%s`: %s\n" % (name, str(e)))
        exit(1)

    sys.stderr.write("Could not find machine `%s` in namespace `%s`.\n" % (name, namespace))
    exit(1)


def open_pod_stream(core_api, name, namespace):
    return "kubectl -n %s exec -it %s -- bash" % (namespace, name)


def connect_to_pod(name, path):
    k8s_utils.load_kube_config()

    core_api = core_v1_api.CoreV1Api()

    namespace = k8s_utils.get_namespace_name(str(u.generate_urlsafe_hash(path)))

    # From deployment name, search the pod inside that deployment
    pod_name = get_pod_name_by_deployment_name(core_api, name, namespace)
    
    # After getting the pod name, check if its status is Ready
    while True:
        response = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)

        if response.status.phase != 'Pending':
            break

        time.sleep(2)

    return open_pod_stream(core_api, pod_name, namespace)
