import sys
import time
import select
import utils as u

from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

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


# def _find_getch():
#     try:
#         import termios
#     except ImportError:
#         # Non-POSIX. Return msvcrt's (Windows') getch.
#         import msvcrt
#         return msvcrt.getch
#
#     # POSIX system. Create and return a getch that manipulates the tty.
#     import sys, tty
#     def _getch():
#
#         try:
#
#
#         finally:
#
#         return ch
#
#     return _getch


def open_pod_stream(core_api, name, namespace):
    # # Open a connection to the pod
    # pod_stream = stream(core_api.connect_get_namespaced_pod_exec,
    #                     name,
    #                     namespace,
    #                     command='/bin/bash',
    #                     stderr=True,
    #                     stdin=True,
    #                     stdout=True,
    #                     tty=True,
    #                     _preload_content=False
    #                     )
    #
    # fd = sys.stdin.fileno()
    # old_settings = termios.tcgetattr(fd)
    # tty.setraw(fd)
    #
    # while pod_stream.is_open():
    #     pod_stream.update(timeout=1)
    #
    #     if pod_stream.peek_stdout():
    #         sys.stdout.write(pod_stream.read_stdout())
    #     if pod_stream.peek_stderr():
    #         sys.stderr.write(pod_stream.read_stderr())
    #
    #     if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
    #         user_input = sys.stdin.read(1)
    #         pod_stream.write_stdin(user_input)
    #
    # termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    #
    # pod_stream.close()ù

    # TODO: This is a temporary workaround!
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

        # print "Machine is not ready... Waiting..."

        time.sleep(2)

    # print "Machine is ready. Connecting..."

    return open_pod_stream(core_api, pod_name, namespace)
