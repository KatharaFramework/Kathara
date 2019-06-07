import json
import sys

import netkit_commons as nc
from kubernetes import client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException


def deploy_namespace(namespace_name):
    core_api = core_v1_api.CoreV1Api()

    namespace_def = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace_name))

    if not nc.PRINT:
        try:
            core_api.create_namespace(namespace_def)
        except ApiException:
            sys.stderr.write("ERROR: could not create namespace `%s`" % namespace_name + "\n")
    else:   # If print mode, prints the pod definition as a JSON on stderr
        sys.stderr.write(json.dumps(namespace_def.to_dict(), indent=True) + "\n\n")


def delete(namespace_name):
    core_api = core_v1_api.CoreV1Api()

    try:
        core_api.delete_namespace(namespace_name)
    except ApiException:
        sys.stderr.write("ERROR: could not delete namespace `%s`" % namespace_name + "\n")