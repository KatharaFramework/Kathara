import base64
import json
import shutil
import sys
import tarfile
import tempfile

import netkit_commons as nc
from kubernetes import client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException

import k8s_utils


def build_k8s_config_map(namespace, lab_path):
    temp_path = tempfile.mkdtemp()

    with tarfile.open("%s/hostlab.tar.gz" % temp_path, "w:gz") as tar:
        tar.add("%s" % lab_path, arcname='.')

    with open("%s/hostlab.tar.gz" % temp_path, "rb") as tar_file:
        tar_data = tar_file.read()

    shutil.rmtree(temp_path)

    data = dict()
    data["hostlab.b64"] = base64.b64encode(tar_data)

    metadata = client.V1ObjectMeta(name="%s-lab-files" % namespace, deletion_grace_period_seconds=0)
    config_map = client.V1ConfigMap(api_version="v1", kind="ConfigMap", data=data, metadata=metadata)

    return config_map


def build_k8s_pod_for_machine(machine):
    # Defines volume mounts for both hostlab and hosthome
    hostlab_volume_mount = client.V1VolumeMount(name="hostlab", mount_path="/tmp/kathara")
    hosthome_volume_mount = client.V1VolumeMount(name="hosthome", mount_path="/hosthome")

    # Minimum caps to make Quagga work without "privileged" mode.
    container_capabilities = client.V1Capabilities(add=["NET_ADMIN", "NET_RAW", "NET_BROADCAST", "SYS_ADMIN"])
    security_context = client.V1SecurityContext(capabilities=container_capabilities)

    # Container port is declared only if it's defined in machine options
    container_ports = None
    if "port" in machine:
        container_ports = [client.V1ContainerPort(
                            name="kathara",
                            container_port=3000,
                            host_port=machine["port"],
                            protocol="TCP"
                          )]

    # Resources limits are declared only if they're defined in machine options
    resources = None
    if "memory" in machine:
        limits = dict()
        limits["memory"] = machine["memory"]

        resources = client.V1ResourceRequirements(limits=limits)

    # postStart lifecycle hook is launched asynchronously by k8s_bin master when the main container is Ready.
    # On Ready state, the pod has volumes and network interfaces up, so this hook is used
    # to execute custom commands coming from .startup file and "exec" option
    lifecycle = None
    if machine["startup_commands"] and len(machine["startup_commands"]) > 0:
        post_start = client.V1Handler(
                        _exec=client.V1ExecAction(
                            command=["/bin/bash", "-c", "; ".join(machine["startup_commands"])]
                        )
                     )
        lifecycle = client.V1Lifecycle(post_start=post_start)

    # Container definition
    kathara_container = client.V1Container(
                            name="kathara",
                            image="%s:latest" % machine["image"],
                            lifecycle=lifecycle,
                            stdin=True,
                            image_pull_policy="IfNotPresent",
                            ports=container_ports,
                            resources=resources,
                            volume_mounts=[hostlab_volume_mount, hosthome_volume_mount],
                            security_context=security_context
                        )

    # Creates networks annotation and metadata definition
    annotations = dict()
    annotations["k8s.v1.cni.cncf.io/networks"] = ", ".join(machine["interfaces"])
    metadata = client.V1ObjectMeta(name=machine["name"], deletion_grace_period_seconds=0, annotations=annotations)

    # Adds fake DNS just to override k8s_bin one
    dns_config = client.V1PodDNSConfig(nameservers=["127.0.0.1"])

    # Define volumes
    # Hostlab is the lab directory mounted from the kubemaster through NFS (read only mode)
    hostlab_volume = client.V1Volume(
                        name="hostlab",
                        config_map=client.V1ConfigMapVolumeSource(
                            name="%s-lab-files" % machine['namespace']
                        )
                     )
    # Hosthome is the current user home directory
    hosthome_volume = client.V1Volume(
                        name="hosthome",
                        host_path=client.V1HostPathVolumeSource(path='/home')
                      )

    spec = client.V1PodSpec(
                containers=[kathara_container],
                dns_policy="None",
                dns_config=dns_config,
                volumes=[hostlab_volume, hosthome_volume]
           )

    return client.V1Pod(api_version="v1", kind="Pod", metadata=metadata, spec=spec)


def deploy(machines, options, netkit_to_k8s_links, lab_path, namespace="default"):
    # Init API Client
    core_api = core_v1_api.CoreV1Api()

    # Config Map will contain lab data to mount into the container as a volume.
    config_map = build_k8s_config_map(namespace, lab_path)
    if not nc.PRINT:    
        core_api.create_namespaced_config_map(body=config_map, namespace=namespace)
    else:
        sys.stderr.write(json.dumps(config_map.to_dict(), indent=True) + "\n\n")

    for machine_name, interfaces in machines.items():
        print "Deploying machine `%s`..." % machine_name

        # Creates a dict containing all current machine info, so it can be passed to build_k8s_pod_for_machine to
        # create a custom pod definition
        current_machine = {
            "namespace": namespace,
            "name": k8s_utils.build_k8s_name(machine_name),
            # TODO: Handle interface namespacing!
            "interfaces": [netkit_to_k8s_links[interface_name] for interface_name, _ in interfaces],
            "image": nc.DOCKER_HUB_PREFIX + nc.IMAGE_NAME,
            "lab_path": lab_path,
            "startup_commands": []
        }

        # Build the postStart commands.
        startup_commands = [
            # If execution flag file is found, abort (this means that postStart has been called again)
            # If not flag the startup execution with a file
            "if [ -f \"/tmp/post_start\" ]; then exit; else touch /tmp/post_start; fi",

            # Removes /etc/bind already existing configuration from k8s_bin internal DNS
            "rm -Rf /etc/bind/*",

            # Parse hostlab.b64
            "base64 -d /tmp/kathara/hostlab.b64 > /hostlab.tar.gz",
            # Extract hostlab.tar.gz data into /hostlab
            "mkdir /hostlab",
            "tar xvfz /hostlab.tar.gz -C /hostlab; rm -f hostlab.tar.gz",

            # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
            # In this way, files are all replaced in the container root folder
            "if [ -d \"/hostlab/{machine_name}\" ]; then " \
            "mkdir /machine_data; cp -rp /hostlab/{machine_name}/* /machine_data; " \
            "chmod -R 777 /machine_data/*; " \
            "cp -rfp /machine_data/* /; fi".format(machine_name=machine_name),

            # Patch the /etc/resolv.conf file. If present, replace the content with the one of the machine.
            # If not, clear the content of the file.
            # This should be patched with "cat" because file is already in use by k8s_bin internal DNS.
            "if [ -f \"/machine_data/etc/resolv.conf\" ]; then " \
            "cat /machine_data/etc/resolv.conf > /etc/resolv.conf; else " \
            "echo \"\" > /etc/resolv.conf; fi",

            # Create /var/log/zebra folder
            "mkdir /var/log/zebra",

            # Give proper permissions to few files/directories (copied from Kathara)
            "chmod -R 777 /var/log/quagga; chmod -R 777 /var/log/zebra; chmod -R 777 /var/www/*",

            # If .startup file is present
            "if [ -f \"/hostlab/{machine_name}.startup\" ]; then " \
            # Copy it from the hostlab directory into the root folder of the container
            "cp /hostlab/{machine_name}.startup /; " \
            # Give execute permissions to the file and execute it
            # We redirect the output "&>" to a random file so we avoid blocking stdin/stdout 
            "chmod u+x /{machine_name}.startup; /{machine_name}.startup &> /tmp/startup_out; " \
            # Delete the file after execution
            "rm /{machine_name}.startup; fi".format(machine_name=machine_name),

            # Delete machine data folder after everything is ready
            "rm -Rf /machine_data"
        ]

        # Saves extra options for current machine
        if options.get(machine_name):
            for opt, val in options[machine_name]:
                if opt == 'mem' or opt == 'M':
                    current_machine["memory"] = val.upper()
                if opt == 'image' or opt == 'i' or opt == 'model-fs' or opt == 'm' or opt == 'f' or opt == 'filesystem':
                    current_machine["image"] = nc.DOCKER_HUB_PREFIX + val
                if opt == 'eth':
                    # TODO: Ask what's this
                    pass

                    # app = val.split(":")
                    # create_network_commands.append(create_network_template + prefix + app[1])
                    # repls = ('{link}', app[1]), ('{machine_name}', machine_name)
                    # create_connection_commands.append(u.replace_multiple_items(repls, create_connection_template))
                    # if not PRINT: u.write_temp(" " + prefix + app[1], u.generate_urlsafe_hash(path) + '_links', PLATFORM)
                    # repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.eth'+str(app[0])+'.rp_filter=0"'), ('{params}', '')
                    # startup_commands.insert(4, u.replace_multiple_items(repls, exec_template))
                if opt == 'bridged':
                    # TODO: Bridged is not supported for now
                    pass
                if opt == 'e' or opt == 'exec':
                    stripped_command = val.strip().replace('\\', r'\\').replace('"', r'\"').replace("'", r"\'")
                    startup_commands.append(stripped_command)
                if opt == 'port':
                    try:
                        current_machine["port"] = int(val)
                    except ValueError:
                        pass

        # Assign it here, because an extra exec command can be found in options and appended
        current_machine["startup_commands"] = startup_commands

        pod = build_k8s_pod_for_machine(current_machine)

        if not nc.PRINT:
            try:
                core_api.create_namespaced_pod(body=pod, namespace=namespace)
                print "Machine `%s` deployed successfully!" % machine_name
            except ApiException:
                sys.stderr.write("ERROR: could not deploy machine `%s`" % machine_name + "\n")
        else:               # If print mode, prints the pod definition as a JSON on stderr
            sys.stderr.write(json.dumps(pod.to_dict(), indent=True) + "\n\n")


def delete(machine_name, namespace, core_api=None):
    core_api = core_v1_api.CoreV1Api() if core_api is None else core_api

    try:
        core_api.delete_namespaced_pod(name=machine_name, namespace=namespace)
        print "Machine `%s` deleted successfully!" % machine_name
    except ApiException:
        sys.stderr.write("ERROR: could not delete machine `%s`" % machine_name + "\n")


def delete_by_namespace(namespace):
    core_api = core_v1_api.CoreV1Api()

    pods = core_api.list_namespaced_pod(namespace=namespace)
    for pod in pods.items:
        delete(pod.metadata.name, namespace, core_api=core_api)

    config_map_name = "%s-lab-files" % namespace
    core_api.delete_namespaced_config_map(name=config_map_name, namespace=namespace)
