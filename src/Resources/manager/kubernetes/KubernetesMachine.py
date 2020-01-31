import logging
from functools import partial
from itertools import islice
from multiprocessing.dummy import Pool
from subprocess import Popen

from progress.bar import Bar

from ... import utils
from ...exceptions import MachineAlreadyExistsError
from ...setting.Setting import Setting

from kubernetes.client.apis import apps_v1_api
from kubernetes import client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from .KubernetesConfigMap import KubernetesConfigMap
import json
from kubernetes.stream import stream

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.startup_commands
STARTUP_COMMANDS = [
    # If execution flag file is found, abort (this means that postStart has been called again)
    # If not flag the startup execution with a file
    "if [ -f \"/tmp/post_start\" ]; then exit; else touch /tmp/post_start; fi",

    # Removes /etc/bind already existing configuration from k8s internal DNS
    "rm -Rf /etc/bind/*",

    # Parse hostlab.b64
    "base64 -d /tmp/kathara/hostlab.b64 > /hostlab.tar.gz",
    # Extract hostlab.tar.gz data into /hostlab
    "mkdir /hostlab",
    "tar xmfz /hostlab.tar.gz -C /hostlab; rm -f hostlab.tar.gz",

    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    # rsync is used to keep symlinks while copying files.
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "rsync -r -K /hostlab/{machine_name}/* /; fi",

    # Patch the /etc/resolv.conf file. If present, replace the content with the one of the machine.
    # If not, clear the content of the file.
    # This should be patched with "cat" because file is already in use by Docker internal DNS.
    "if [ -f \"/hostlab/{machine_name}/etc/resolv.conf\" ]; then " \
    "cat /hostlab/{machine_name}/etc/resolv.conf > /etc/resolv.conf; else " \
    "echo \"\" > /etc/resolv.conf; fi",

    # Give proper permissions to /var/www
    "chmod -R 777 /var/www/*",

    # Give proper permissions to Quagga files (if present)
    "if [ -d \"/etc/quagga\" ]; then "
    "chown quagga:quagga /etc/quagga/*",
    "chmod 640 /etc/quagga/*; fi",

    # If shared.startup file is present
    "if [ -f \"/hostlab/shared.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a debugging file
    "chmod u+x /hostlab/shared.startup",
    # Adds a line to enable command output
    "sed -i \"1s;^;set -x\\n\\n;\" /hostlab/shared.startup",
    "/hostlab/shared.startup &> /var/log/shared.log; fi",

    # If .startup file is present
    "if [ -f \"/hostlab/{machine_name}.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a debugging file
    "chmod u+x /hostlab/{machine_name}.startup",
    # Adds a line to enable command output
    "sed -i \"1s;^;set -x\\n\\n;\" /hostlab/{machine_name}.startup",
    "/hostlab/{machine_name}.startup &> /var/log/startup.log; fi",

    # Remove the Kubernetes' default gateway which points to the eth0 interface and causes problems sometimes.
    "route del default dev eth0 &> /dev/null",

    # Placeholder for user commands
    "{machine_commands}"
]

SHUTDOWN_COMMANDS = [
    # If machine.shutdown file is present
    "if [ -f \"/hostlab/{machine_name}.shutdown\" ]; then "
    # Give execute permissions to the file and execute it
    "chmod u+x /hostlab/{machine_name}.shutdown; /hostlab/{machine_name}.shutdown; fi",

    # If shared.shutdown file is present
    "if [ -f \"/hostlab/shared.shutdown\" ]; then "
    # Give execute permissions to the file and execute it
    "chmod u+x /hostlab/shared.shutdown; /hostlab/shared.shutdown; fi"
]


class KubernetesMachine(object):
    __slots__ = ['client', 'core_client', 'kubernetes_config_map']

    def __init__(self):
        self.client = apps_v1_api.AppsV1Api()
        self.core_client = core_v1_api.CoreV1Api()

        self.kubernetes_config_map = KubernetesConfigMap()

    def deploy_machines(self, lab, privileged_mode=False):
        machines = lab.machines.items()
        progress_bar = Bar('Deploying machines...', max=len(machines))

        # Deploy all lab machines.
        # If there is no lab.dep file, machines can be deployed using multithreading.
        # If not, they're started sequentially
        if not lab.has_dependencies:
            pool_size = utils.get_pool_size()
            machines_pool = Pool(pool_size)

            items = utils.chunk_list(machines, pool_size)

            for chunk in items:
                machines_pool.map(func=partial(self._deploy_machine, progress_bar, privileged_mode),
                                  iterable=chunk
                                  )
        else:
            for item in machines:
                self._deploy_machine(progress_bar, privileged_mode, item)

        progress_bar.finish()

    def _deploy_machine(self, progress_bar, privileged_mode, machine_item):
        (_, machine) = machine_item

        self.create(machine, privileged=privileged_mode)

        progress_bar.next()

    def create(self, machine, privileged=False):
        logging.debug("Creating machine `%s`..." % machine.name)

        # Get the general options into a local variable (just to avoid accessing the lab object every time)
        options = machine.lab.general_options

        # If bridged is defined for the device, throw a warning.
        if "bridged" in options or machine.bridge:
            logging.warning('Bridged option is not supported on Kubernetes. It will be ignored.')

        # If any exec command is passed in command line, add it.
        if "exec" in options:
            machine.add_meta("exec", options["exec"])

        # TODO: ADD TO K8S
        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}

        sysctl_parameters["net.ipv4.ip_forward"] = 1
        sysctl_parameters["net.ipv4.icmp_ratelimit"] = 0

        if Setting.get_instance().enable_ipv6:
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 1
            sysctl_parameters["net.ipv6.icmp.ratelimit"] = 0
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 0
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 0

        machine.add_meta("sysctls", sysctl_parameters)
        machine.add_meta("privileged", privileged)

        config_map = self.kubernetes_config_map.deploy_for_machine(machine)
        machine_definition = self._build_definition(machine, config_map)

        # TODO: Exception Already exists
        machine.api_object = self.client.create_namespaced_deployment(body=machine_definition,
                                                                      namespace=machine.lab.folder_hash
                                                                      )

    def undeploy(self, lab_hash, selected_machines=None):
        machines = self.get_machines_by_filters(lab_hash=lab_hash)

        pool_size = utils.get_pool_size()
        machines_pool = Pool(pool_size)

        items = utils.chunk_list(machines, pool_size)

        progress_bar = Bar("Deleting machines...", max=len(machines))

        for chunk in items:
            machines_pool.map(func=partial(self._undeploy_machine, selected_machines, True, progress_bar),
                              iterable=chunk
                              )

        progress_bar.finish()

    def wipe(self):
        machines = self.get_machines_by_filters()

        pool_size = utils.get_pool_size()
        machines_pool = Pool(pool_size)

        items = utils.chunk_list(machines, pool_size)

        for chunk in items:
            machines_pool.map(func=partial(self._undeploy_machine, [], False, None), iterable=chunk)

    def _undeploy_machine(self, selected_machines, log, progress_bar, machine_item):
        # If selected machines list is empty, remove everything
        # Else, check if the machine is in the list.
        if not selected_machines or \
           machine_item.metadata.labels["name"] in selected_machines:
            self.delete_machine(machine_item)

            if log:
                progress_bar.next()

    def connect(self, lab_hash, machine_name, shell, logs=False):
        pass

    @staticmethod
    def exec(container, command):
        pass

    @staticmethod
    def copy_files(machine, path, tar_data):
        pass

    def get_machines_by_filters(self, lab_hash=None, machine_name=None):
        filters = ["app=kathara"]
        if machine_name:
            filters.append("name=%s" % machine_name)

        return self.core_client.list_namespaced_pod(namespace=lab_hash if lab_hash else "default",
                                                    label_selector=",".join(filters)
                                                    ).items

    def get_machine(self, lab_hash, machine_name):
        containers = self.get_machines_by_filters(lab_hash=lab_hash, machine_name=machine_name)

        logging.debug("Found containers: %s" % str(containers))

        if len(containers) != 1:
            raise Exception("Error getting the machine `%s` inside the lab." % machine_name)
        else:
            return containers[0]

    def _build_definition(self, machine, config_map):
        volume_mounts = []
        if config_map:
            # Define volume mounts for hostlab if a ConfigMap is defined.
            volume_mounts.append(client.V1VolumeMount(name="hostlab", mount_path="/tmp/kathara"))

        if machine.meta["privileged"]:
            security_context = client.V1SecurityContext(privileged=True)
        else:
            security_context = client.V1SecurityContext(capabilities=client.V1Capabilities(add=machine.capabilities))

        port_info = machine.get_ports()
        container_ports = None
        if port_info:
            (internal_port, protocol, host_port) = port_info
            container_ports = [
                client.V1ContainerPort(
                    name="kathara",
                    container_port=internal_port,
                    host_port=host_port,
                    protocol=protocol
                )
            ]

        resources = None
        memory = machine.get_mem()
        cpus = machine.get_cpu(multiplier=1000)
        if memory or cpus:
            limits = dict()
            if memory:
                limits["memory"] = memory.upper()
            if cpus:
                limits["cpu"] = "%dm" % cpus

            resources = client.V1ResourceRequirements(limits=limits)

        # postStart lifecycle hook is launched asynchronously by k8s master when the main container is Ready
        # On Ready state, the pod has volumes and network interfaces up, so this hook is used
        # to execute custom commands coming from .startup file and "exec" option
        # Build the final startup commands string
        startup_commands_string = "; ".join(STARTUP_COMMANDS) \
                                      .format(machine_name=machine.name,
                                              machine_commands="; ".join(machine.startup_commands)
                                              )

        post_start = client.V1Handler(
            _exec=client.V1ExecAction(
                command=[Setting.get_instance().device_shell, "-c", startup_commands_string]
            )
        )
        lifecycle = client.V1Lifecycle(post_start=post_start)

        # Main Container definition
        container_definition = client.V1Container(
            name=machine.name,
            image=machine.get_image(),
            lifecycle=lifecycle,
            stdin=True,
            tty=True,
            image_pull_policy="Always",
            ports=container_ports,
            resources=resources,
            volume_mounts=volume_mounts,
            security_context=security_context
        )

        # Create annotations
        pod_annotations = {}

        network_interfaces = []
        for (_, machine_link) in machine.interfaces.items():
            network_interfaces.append({
                "name": machine_link.api_object["metadata"]["name"],
                "namespace": machine.lab.folder_hash
            })

        # Convert the dict into a JSON string and assign it to the Pod annotation
        pod_annotations["k8s.v1.cni.cncf.io/networks"] = json.dumps(network_interfaces)

        # Create labels (so Deployment can match them)
        pod_labels = {"name": machine.name,
                      "app": "kathara"
                      }

        pod_metadata = client.V1ObjectMeta(name="%s-pod" % self.get_full_name(machine.name),
                                           deletion_grace_period_seconds=0,
                                           annotations=pod_annotations,
                                           labels=pod_labels
                                           )

        # Add fake DNS just to override k8s one
        dns_config = client.V1PodDNSConfig(nameservers=["127.0.0.1"])

        # Define volumes
        volumes = []
        if config_map:
            # Hostlab is the lab base64 encoded .tar.gz of the machine files, deployed as a ConfigMap in the cluster
            # The base64 file is mounted into /tmp and it's extracted by the postStart hook
            volumes.append(client.V1Volume(
                name="hostlab",
                config_map=client.V1ConfigMapVolumeSource(
                    name="%s-%s-files" % (machine.name, machine.lab.folder_hash)
                )
            ))

        # Create PodSpec containing all the info associated with this machine
        pod_spec = client.V1PodSpec(containers=[container_definition],
                                    dns_policy="None",
                                    dns_config=dns_config,
                                    volumes=volumes,
                                    )

        # TODO: SCHEDULER
        # # Assign node selector only if there's a constraint given by the scheduler
        # if machine["node_selector"] is not None:
        #     node_expression = client.V1NodeSelectorRequirement(key="kubernetes.io/hostname",
        #                                                        operator="In",
        #                                                        values=[machine["node_selector"]]
        #                                                        )
        #
        #     node_preference = client.V1PreferredSchedulingTerm(
        #         preference=client.V1NodeSelectorTerm(match_expressions=[node_expression]),
        #         weight=100
        #     )
        #
        #     pod_spec.affinity = client.V1Affinity(
        #         node_affinity=client.V1NodeAffinity(
        #             preferred_during_scheduling_ignored_during_execution=[node_preference])
        #     )

        # Create PodTemplate which is used by Deployment
        pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)

        # Defines selection rules for the Deployment, labels to match are the same as the ones defined in PodSpec
        selector_rules = client.V1LabelSelector(match_labels=pod_labels)

        # Create Deployment Spec, here we set the previous PodTemplate and the selector rules
        deployment_spec = client.V1DeploymentSpec(replicas=1,
                                                  template=pod_template,
                                                  selector=selector_rules
                                                  )

        # Create Deployment metadata, also this object is marked with the same labels of the Pod
        deployment_metadata = client.V1ObjectMeta(name=self.get_full_name(machine.name), labels=pod_labels)

        return client.V1Deployment(api_version="apps/v1",
                                   kind="Deployment",
                                   metadata=deployment_metadata,
                                   spec=deployment_spec
                                   )

    @staticmethod
    def get_full_name(name):
        return "%s-%s" % (Setting.get_instance().device_prefix, name)

    def delete_machine(self, machine):
        machine_name = machine.metadata.labels["name"]
        machine_namespace = machine.metadata.namespace

        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=machine_name)

        # Retrieve the pod of current Deployment
        container = self.get_machine(lab_hash=machine_namespace, machine_name=machine_name)

        # Execute the shutdown commands inside the Pod
        stream(self.core_client.connect_get_namespaced_pod_exec,
               name=container.metadata.name,
               namespace=machine_namespace,
               command=[Setting.get_instance().device_shell, '-c', shutdown_commands_string],
               stderr=False,
               stdin=False,
               stdout=False,
               tty=False
               )

        self.client.delete_namespaced_deployment(name=machine_name,
                                                 namespace=machine_namespace
                                                 )
