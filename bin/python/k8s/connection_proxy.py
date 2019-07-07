import sys
import time

from kubernetes.client.apis import core_v1_api
from kubernetes.client.apis import apps_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

import k8s_utils


def get_pod_name_by_deployment_name(name, namespace):
    apps_api = apps_v1_api.AppsV1Api()

    try:
        deployment_info = apps_api.read_namespaced_deployment(name=name, namespace=namespace)
        return deployment_info.spec.template.metadata.name
    except ApiException as e:
        sys.stderr.write("Could not find machine %s in namespace %s." % (name, namespace))
        exit(1)


def open_pod_stream(core_api, name, namespace):
    # Open a connection to the pod
    pod_stream = core_api.connect_get_namespaced_pod_exec(
                        name,
                        namespace,
                        command='/bin/bash',
                        stderr=True,
                        stdin=True,
                        stdout=True,
                        tty=True,
                        _preload_content=False
                        )

    # while pod_stream.is_open():
    #     pod_stream.update(timeout=1)
    #
    #     if pod_stream.peek_stdout():
    #         sys.stdout.write(pod_stream.read_stdout())
    #     if pod_stream.peek_stderr():
    #         sys.stderr.write(pod_stream.read_stderr())
    #
    #     user_input = sys.stdin.readline()
    #     pod_stream.write_stdin(user_input)
    #
    # pod_stream.close()


def connect_to_pod(name, namespace='default'):
    k8s_utils.load_kube_config()

    # From deployment name, search the pod inside that deployment
    pod_name = get_pod_name_by_deployment_name(name, namespace)

    core_api = core_v1_api.CoreV1Api()
    # After getting the pod name, check if it's status is Ready
    while True:
        response = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)

        if response.status.phase != 'Pending':
            break

        print "Machine is not ready... Waiting..."

        time.sleep(1)

    print "Machine is ready. Connecting..."

    open_pod_stream(core_api, pod_name, namespace)
