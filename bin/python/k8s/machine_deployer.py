import os
import socket
import sys
import json

import netkit_commons as nc
from kubernetes import client
from kubernetes.client.apis import core_v1_api


def build_k8s_pod_for_machine(machine):
    # Defines volume mounts for both hostlab and hosthome
    hostlab_volume_mount = client.V1VolumeMount(name="hostlab", mount_path="/hostlab")
    hosthome_volume_mount = client.V1VolumeMount(name="hosthome", mount_path="/hosthome")

    # Minimum caps to make Quagga work without "privileged" mode.
    container_capabilities = client.V1Capabilities(add=["NET_ADMIN", "NET_RAW", "SYS_ADMIN"])
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

    # postStart lifecycle hook is launched asynchronously by k8s master when the main container is Ready.
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
                            image="docker.io/%s:latest" % machine["image"],
                            lifecycle=lifecycle,
                            tty=True,
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

    # Adds fake DNS just to override k8s one
    dns_config = client.V1PodDNSConfig(nameservers=["127.0.0.1"])

    # Define volumes
    # Hostlab is the lab directory mounted from the kubemaster through NFS (read only mode)
    hostlab_volume = client.V1Volume(
                        name="hostlab",
                        nfs=client.V1NFSVolumeSource(
                            server=socket.gethostname(),    # Since we use Kathara from a master, and NFS server
                                                            # is on a master, we get the current hostname
                            path=machine["lab_path"],
                            read_only=True
                        )
                     )
    # Hosthome is the current user home directory
    hosthome_volume = client.V1Volume(
                        name="hosthome",
                        host_path=client.V1HostPathVolumeSource(path=os.path.expanduser('~'))
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

    for machine_name, interfaces in machines.items():
        print "Deploying machine `%s`..." % machine_name

        # Creates a dict containing all current machine info, so it can be passed to build_k8s_pod_for_machine to
        # create a custom pod definition
        current_machine = {
            "namespace": namespace,
            "name": machine_name,
            "interfaces": [netkit_to_k8s_links[interface_name] for interface_name, _ in interfaces],
            "image": nc.DOCKER_HUB_PREFIX + nc.IMAGE_NAME,
            "lab_path": lab_path,
            "startup_commands": []
        }

        # Build the postStart commands.
        startup_commands = [
            # If execution mark file is found, abort (this means that postStart has been called again)
            # If not mark the startup execution with a file
            "if [ -f \"/tmp/post_start\" ]; then exit; else touch /tmp/post_start; fi",

            # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
            # In this way, files are all replaced in the container root folder
            "if [ -d \"/hostlab/{machine_name}\" ]; then cp -rfp /hostlab/{machine_name}/* /; fi" % {'machine_name': machine_name},

            # Create /var/log/zebra folder
            "mkdir /var/log/zebra",

            # Give proper permissions to few files/directories (copied from Kathara)
            "chmod -R 777 /var/log/quagga; chmod -R 777 /var/log/zebra; chmod -R 777 /var/www/*",

            # Removes /etc/bind already existing configuration from k8s internal DNS
            "rm -Rf /etc/bind/*",

            # Patch the /etc/resolv.conf file. If present, replace the content with the one of the machine.
            # If not, clear the content of the file.
            # This should be patched with "cat" because file is already in use by k8s internal DNS.
            "if [ -f \"/hostlab/{machine_name}/etc/resolv.conf\" ]; then " \
            "cat /hostlab/{machine_name}/etc/resolv.conf > /etc/resolv.conf; else" \
            "cat \"\" > /etc/resolv.conf; fi" % {'machine_name': machine_name},

            # If .startup file is present
            "if [ -f \"/hostlab/{machine_name}.startup\" ]; then " \
            # Copy it from the hostlab directory into the root folder of the container
            "cp /hostlab/{machine_name}.startup /;" \
            # Give execute permissions to the file and execute it
            "chmod u+x /{machine_name}.startup; /{machine_name}.startup;" \
            # Delete the file after execution
            "rm /{machine_name}.startup; fi" % {'machine_name': machine_name}
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
            core_api.create_namespaced_pod(body=pod, namespace=namespace)
        else:               # If print mode, prints the pod definition as a JSON on stderr
            sys.stderr.write(json.dumps(pod.to_dict(), indent=True))
