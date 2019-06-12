import re

import netkit_commons as nc
from kubernetes import config, client


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
            eth_options = [v for (k, v) in options.get(machine_name) if k == "eth"]

            for val in eth_options:
                extra_links.append(val.split(":")[1])

    return set(extra_links)


def load_kube_config():
    try:
        config.load_kube_config()           # Try to load configuration if Kathara is launched on a k8s master.
    except Exception:                       # Not on a k8s master, load Kathara config to read remote cluster data.
        # Try to read configuration. If this fails, throw an Exception.
        try:
            api_url = nc.kat_config['api_url']
            token = nc.kat_config['token']
        except Exception:
            raise Exception("Cannot read Kubernetes configuration from Kathara.")

        # Load the configuration and set it as default.
        configuration = client.Configuration()
        configuration.host = api_url
        configuration.api_key = {"authorization": "Bearer " + token}

        client.Configuration.set_default(configuration)
