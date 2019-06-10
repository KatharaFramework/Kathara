import re

from kubernetes import config


def build_k8s_name(resource_name, prefix=""):
    # K8s names should be only alphanumeric lowercase + "-" + "."
    new_resource_name = resource_name.lower()
    new_resource_name = re.sub('[^0-9a-z\-\.]+', '', new_resource_name)
    return (prefix + "-" if prefix != "" else "") + new_resource_name


def get_namespace_name(hash_name):
    name = build_k8s_name(hash_name)
    return name[0:7]


def get_extra_links_from_machine_options(machines, options):
    extra_links = []

    for machine_name in machines:
        if options.get(machine_name):
            eth_options = {k: options[machine_name][k] for k, v in options[machine_name]}

            for val in eth_options:
                extra_links.append(val.split(":")[1])

    return extra_links


def load_kube_config():
    # TODO: Add Custom API User configuration
    config.load_kube_config()
