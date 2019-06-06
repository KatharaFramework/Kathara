import re

from kubernetes import config


def build_k8s_name(resource_name, prefix=""):
    # K8s names should be only alphanumeric lowercase + "-" + "."
    new_resource_name = resource_name.lower()
    new_resource_name = re.sub('[^0-9a-z\-\.]+', '', new_resource_name)
    return (prefix + "-" if prefix != "" else "") + new_resource_name


def get_namespace_name(hash_name):
    name = build_k8s_name(hash_name)
    return name[0:8]


def load_kube_config():
    # TODO: Add Custom API User configuration
    config.load_kube_config()
