import json
import os
import sys

import netkit_commons as nc
from kubernetes.client.rest import ApiException
from kubernetes.client.apis import custom_objects_api

import k8s_utils

group = "k8s_bin.cni.cncf.io"
version = "v1"
plural = "network-attachment-definitions"


base_path = os.path.join(os.environ['NETKIT_HOME'], 'temp')
if nc.PLATFORM != nc.WINDOWS:
    base_path = os.path.join(os.environ['HOME'], 'netkit_temp')


def read_network_counter(network_counter):
    # If the file doesn't exists, create an empty one.
    if not os.path.exists(os.path.join(base_path, 'last_network_counter.txt')):
        last_network_counter = open(os.path.join(base_path, 'last_network_counter.txt'), 'w')
        last_network_counter.close()

    # Reads the value from the file
    with open(os.path.join(base_path, 'last_network_counter.txt'), 'r') as last_network_counter:
        # Means it was not set by user
        if network_counter == 0:
            try:
                network_counter = int(last_network_counter.readline())
            except ValueError:
                network_counter = 0

    return network_counter


def write_network_counter(network_counter):
    # Writes the new value in the file
    with open(os.path.join(base_path, 'last_network_counter.txt'), 'w') as last_network_counter:
        last_network_counter.write(str(network_counter))


def build_k8s_definition_for_link(link_name, network_counter):
    # Creates a dict which contains the "link" network definition to deploy in k8s_bin
    # TODO: Handle namespacing
    return {
        "apiVersion": "k8s_bin.cni.cncf.io/v1",
        "kind": "NetworkAttachmentDefinition",
        "metadata": {
            "name": link_name
        },
        "spec": {
            "config": """{
                        "cniVersion": "0.3.0",
                        "type": "kathara",
                        "vlanId": %d
                    }""" % (10 + network_counter)
        }
    }


def deploy_links(links, namespace="default", network_counter=0):
    # Init API Client
    custom_api = custom_objects_api.CustomObjectsApi()

    # Reads the network counter. In k8s_bin case, the counter is used for VXLAN ID tag.
    network_counter = read_network_counter(network_counter)

    created_links = {}      # Associates each netkit link name to a k8s_bin name. This will be used later both to write
                            # which links are part of the lab and to map machine's collision domains to k8s_bin networks
    for link in links:
        print "Deploying link `%s`..." % link

        link_name = k8s_utils.build_k8s_name(link, prefix="net")
        net_attach_def = build_k8s_definition_for_link(link_name, network_counter)
        if not nc.PRINT:
            try:
                custom_api.create_namespaced_custom_object(group, version, namespace, plural, net_attach_def)
                print "Link `%s` deployed successfully as `%s`!" % (link, link_name)
            except ApiException:
                sys.stderr.write("ERROR: could not deploy link `%s`" % link + "\n")
        else:               # If print mode, prints the "link" network definition as a JSON on stderr
            sys.stderr.write(json.dumps(net_attach_def, indent=True) + "\n\n")

        network_counter += 1
        created_links[link] = link_name

    # Writes the new network counter back.
    write_network_counter(network_counter)

    return created_links


def delete(link_name, namespace, custom_api=None):
    custom_api = custom_objects_api.CustomObjectsApi() if custom_api is None else custom_api

    try:
        custom_api.delete_namespaced_custom_object(group, version, namespace, plural, link_name, {})
        print "Link `%s` deleted successfully!" % link_name
    except ApiException:
        sys.stderr.write("ERROR: could not delete link `%s`" % link_name + "\n")


def delete_by_namespace(namespace):
    custom_api = custom_objects_api.CustomObjectsApi()

    net_attach_defs = custom_api.list_namespaced_custom_object(group, version, namespace, plural)
    for net_attach_def in net_attach_defs:
        delete(net_attach_def.metadata.name, namespace, custom_api=custom_api)
