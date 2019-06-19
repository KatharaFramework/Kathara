import os

import netkit_commons as nc
import utils as u
from kubernetes.client.rest import ApiException

import k8s_utils
import link_deployer
import machine_deployer
import namespace_deployer
from scheduler import hierarchical_clustering_scheduler


def deploy(machines, links, options, path, network_counter=0):
    # Loads the configuration of the master if it's not print mode
    if not nc.PRINT:
        k8s_utils.load_kube_config()

    namespace = k8s_utils.get_namespace_name(str(u.generate_urlsafe_hash(path)))

    # Lab is deployed only if associated namespace is created.
    try:
        namespace_deployer.deploy_namespace(namespace)
    except ApiException:
        print "ERROR: Cannot deploy lab on cluster. Still deleting previous deployment..."
        return

    print "Deploying links..."
    # Before deploying links, check if there are any extra links in the machine options
    # This is needed because all the links must be deployed before the machines are created
    extra_links = k8s_utils.get_extra_links_from_machine_options(machines, options)

    netkit_to_k8s_links = link_deployer.deploy_links(
                            links | extra_links,          # Merge the two sets
                            namespace=namespace,
                            network_counter=network_counter
                          )

    print "Running scheduler to assign machines to Kubernetes nodes..."
    node_constraints = hierarchical_clustering_scheduler.get_constraints_for_lab(machines)

    print "Deploying machines..."
    machine_deployer.deploy(
        machines,
        options,
        netkit_to_k8s_links,
        node_constraints,
        path,
        namespace=namespace
    )

    # Writes a temp file just to "flag" that the lab has been deployed
    if not nc.PRINT:
        u.write_temp("", "%s_deploy" % namespace, nc.PLATFORM)


def get_lab_info(path):
    namespace = k8s_utils.get_namespace_name(str(u.generate_urlsafe_hash(path)))

    if not os.path.exists("%s/%s_deploy" % (u.get_temp_folder(nc.PLATFORM), namespace)):
        print "Lab is not deployed."
        return

    k8s_utils.load_kube_config()

    print "========================= Lab Info =========================="

    print "NAMESPACE: %s" % namespace

    machine_deployer.dump_namespace_machines(namespace)
    link_deployer.dump_namespace_links(namespace)


def delete_lab(namespace):
    print "Deleting lab with namespace `%s`..." % namespace

    # Deleting namespace will also delete all resources in it.
    namespace_deployer.delete(namespace)

    # Delete "flag" file.
    try:
        os.remove("%s/%s_deploy" % (u.get_temp_folder(nc.PLATFORM), namespace))
    except OSError:
        # Suppress errors when kclean is called on a non deployed lab.
        pass


def delete(path, filtered_machines=None):
    k8s_utils.load_kube_config()

    namespace = k8s_utils.get_namespace_name(str(u.generate_urlsafe_hash(path)))

    if filtered_machines is not None and len(filtered_machines) > 0:
        # Some machine names are passed, delete only those machines.
        for machine in filtered_machines:
            machine_deployer.delete(machine, namespace)
    else:
        # Clear the entire lab.
        delete_lab(namespace)


def delete_all():
    k8s_utils.load_kube_config()

    temp_files = os.listdir(u.get_temp_folder(nc.PLATFORM))
    # Get all current deployed labs, getting the list of "flag" files in temp folder.
    deploy_temp_files = list(filter(lambda x: "_deploy" in x, temp_files))

    # If no lab is deployed, return.
    if len(deploy_temp_files) <= 0:
        return

    for deploy_temp_file in deploy_temp_files:
        namespace = deploy_temp_file.replace("_deploy", "")
        delete_lab(namespace)
