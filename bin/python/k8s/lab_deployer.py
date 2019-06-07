import os

import netkit_commons as nc
import utils as u

import k8s_utils
import link_deployer
import machine_deployer
import namespace_deployer


def deploy(machines, links, options, path, network_counter=0):
    # Loads the configuration of the master if it's not print mode
    if not nc.PRINT:
        k8s_utils.load_kube_config()

    # namespace = "default"
    namespace = k8s_utils.get_namespace_name(str(u.generate_urlsafe_hash(path)))
    namespace_deployer.deploy_namespace(namespace)

    print "Deploying links..."
    netkit_to_k8s_links = link_deployer.deploy_links(
                            links,
                            namespace=namespace,
                            network_counter=network_counter
                          )

    print "Deploying machines..."
    machine_deployer.deploy(
        machines,
        options,
        netkit_to_k8s_links,
        path,
        namespace=namespace
    )

    # Writes a temp file just to "flag" that the lab has been deployed
    if not nc.PRINT:
        u.write_temp("", "%s_deploy" % namespace, nc.PLATFORM)


def delete_lab(namespace):
    # TODO: Probably with namespaces those two lines are useless.
    machine_deployer.delete_by_namespace(namespace)
    link_deployer.delete_by_namespace(namespace)

    if namespace != "default":
        namespace_deployer.delete(namespace)

    os.remove("%s/%s_deploy" % (u.get_temp_folder(nc.PLATFORM), namespace))


def delete(path, filtered_machines=None):
    k8s_utils.load_kube_config()

    # namespace = "default"
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
    deploy_temp_files = list(filter(lambda x: "_deploy" in x, temp_files))

    for deploy_temp_file in deploy_temp_files:
        namespace = deploy_temp_file.replace("_deploy", "")
        delete_lab(namespace)
