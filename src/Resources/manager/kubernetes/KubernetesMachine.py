import hashlib
import json
import logging
import re
import shlex
from functools import partial
from multiprocessing.dummy import Pool

from kubernetes import client
from kubernetes.client.apis import apps_v1_api
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from progress.bar import Bar

from .KubernetesConfigMap import KubernetesConfigMap
from ... import utils
from ...exceptions import MachineAlreadyExistsError
from ...setting.Setting import Setting
from ...trdparty.k8spty.terminal import KubernetesTerminal

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.startup_commands
STARTUP_COMMANDS = [
    # If execution flag file is found, abort (this means that postStart has been called again)
    # If not flag the startup execution with a file
    "if [ -f \"/tmp/post_start\" ]; then exit; else touch /tmp/post_start; fi",

    "{sysctl_commands}",

    # Removes /etc/bind already existing configuration from k8s internal DNS
    "rm -Rf /etc/bind/*",

    # Parse hostlab.b64
    "base64 -d /tmp/kathara/hostlab.b64 > /hostlab.tar.gz",
    # Extract hostlab.tar.gz data into /
    "tar xmfz /hostlab.tar.gz -C /; rm -f hostlab.tar.gz",

    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    # rsync is used to keep symlinks while copying files.
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "rsync -r -K /hostlab/{machine_name}/* /; fi",

    # Patch the /etc/resolv.conf file. If present, replace the content with the one of the machine.
    # If not, clear the content of the file.
    # This should be patched with "cat" because file is already in use by Kubernetes internal DNS.
    "if [ -f \"/hostlab/{machine_name}/etc/resolv.conf\" ]; then "
    "cat /hostlab/{machine_name}/etc/resolv.conf > /etc/resolv.conf; else "
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
    __slots__ = ['client', 'core_client', 'kubernetes_config_map', 'kubernetes_namespace']

    def __init__(self, kubernetes_namespace):
        self.client = apps_v1_api.AppsV1Api()
        self.core_client = core_v1_api.CoreV1Api()

        self.kubernetes_config_map = KubernetesConfigMap()

        self.kubernetes_namespace = kubernetes_namespace

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

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}

        sysctl_parameters["net.ipv4.ip_forward"] = 1
        sysctl_parameters["net.ipv4.icmp_ratelimit"] = 0

        if Setting.get_instance().enable_ipv6:
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 1
            sysctl_parameters["net.ipv6.icmp.ratelimit"] = 0
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 0
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 0

        # Merge machine sysctls
        machine.meta['sysctls'] = {**sysctl_parameters, **machine.meta['sysctls']}

        try:
            config_map = self.kubernetes_config_map.deploy_for_machine(machine)
            machine_definition = self._build_definition(machine, config_map, privileged)

            machine.api_object = self.client.create_namespaced_deployment(body=machine_definition,
                                                                          namespace=machine.lab.folder_hash
                                                                          )
        except ApiException as e:
            if e.status == 409 and 'Conflict' in e.reason:
                raise MachineAlreadyExistsError("Machine with name `%s` already exists." % machine.name)
            else:
                raise e

    def _build_definition(self, machine, config_map, privileged):
        volume_mounts = []
        if config_map:
            # Define volume mounts for hostlab if a ConfigMap is defined.
            volume_mounts.append(client.V1VolumeMount(name="hostlab", mount_path="/tmp/kathara"))

        if Setting.get_instance().host_shared:
            volume_mounts.append(client.V1VolumeMount(name="shared", mount_path="/shared"))

        # Machine must be executed in privileged mode to run sysctls,
        # and k8s python API does not support sysctls in Pod definition.
        security_context = client.V1SecurityContext(privileged=True)

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
        sysctl_commands = "; ".join(["sysctl %s=%d" % item for item in machine.meta["sysctls"].items()])
        startup_commands_string = "; ".join(STARTUP_COMMANDS) \
                                      .format(machine_name=machine.name,
                                              sysctl_commands=sysctl_commands,
                                              machine_commands="; ".join(machine.startup_commands)
                                              )

        post_start = client.V1Handler(
            _exec=client.V1ExecAction(
                command=[Setting.get_instance().device_shell, "-c", startup_commands_string]
            )
        )
        lifecycle = client.V1Lifecycle(post_start=post_start)

        container_definition = client.V1Container(
            name=self.get_deployment_name(machine.name),
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

        pod_annotations = {}
        network_interfaces = []
        for (idx, machine_link) in machine.interfaces.items():
            # Generate name for the interface
            machine_interface_name = "net%d" % idx

            network_interfaces.append({
                "name": machine_link.api_object["metadata"]["name"],
                "namespace": machine.lab.folder_hash,
                "interface": machine_interface_name
            })
        pod_annotations["k8s.v1.cni.cncf.io/networks"] = json.dumps(network_interfaces)

        # Create labels (so Deployment can match them)
        pod_labels = {"name": machine.name,
                      "app": "kathara"
                      }

        pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                           annotations=pod_annotations,
                                           labels=pod_labels
                                           )

        # Add fake DNS just to override k8s one
        dns_config = client.V1PodDNSConfig(nameservers=["127.0.0.1"])

        volumes = []
        if config_map:
            # Hostlab is the lab base64 encoded .tar.gz of the machine files, deployed as a ConfigMap in the cluster
            # The base64 file is mounted into /tmp and it's extracted by the postStart hook
            volumes.append(client.V1Volume(
                name="hostlab",
                config_map=client.V1ConfigMapVolumeSource(
                    name=self.kubernetes_config_map.build_name_for_machine(machine.name, machine.lab.folder_hash)
                )
            ))

        # Container /shared mounts in /home/shared folder
        if Setting.get_instance().host_shared:
            volumes.append(client.V1Volume(
                name="shared",
                host_path=client.V1HostPathVolumeSource(
                    path='/home/shared',
                    type='DirectoryOrCreate'
                )
            ))

        pod_spec = client.V1PodSpec(containers=[container_definition],
                                    dns_policy="None",
                                    dns_config=dns_config,
                                    volumes=volumes
                                    )

        pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)
        selector_rules = client.V1LabelSelector(match_labels=pod_labels)
        deployment_spec = client.V1DeploymentSpec(replicas=1,
                                                  template=pod_template,
                                                  selector=selector_rules
                                                  )
        deployment_metadata = client.V1ObjectMeta(name=self.get_deployment_name(machine.name), labels=pod_labels)

        return client.V1Deployment(api_version="apps/v1",
                                   kind="Deployment",
                                   metadata=deployment_metadata,
                                   spec=deployment_spec
                                   )

    def undeploy(self, lab_hash, selected_machines=None):
        machines = self.get_machines_by_filters(lab_hash=lab_hash)

        pool_size = utils.get_pool_size()
        machines_pool = Pool(pool_size)

        items = utils.chunk_list(machines, pool_size)

        progress_bar = Bar("Deleting machines...", max=len(machines) if not selected_machines
        else len(selected_machines)
                           )

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
            self._delete_machine(machine_item)

            if log:
                progress_bar.next()

    def _delete_machine(self, machine):
        machine_name = machine.metadata.labels["name"]
        machine_namespace = machine.metadata.namespace

        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=machine_name)

        self.exec(machine_namespace,
                  machine_name,
                  command=[Setting.get_instance().device_shell, '-c', shutdown_commands_string],
                  )

        try:
            self.kubernetes_config_map.delete_for_machine(machine_name, machine_namespace)

            self.client.delete_namespaced_deployment(name=self.get_deployment_name(machine_name),
                                                     namespace=machine_namespace
                                                     )
        except ApiException:
            return

    def connect(self, lab_hash, machine_name, shell=None, logs=False):
        logging.debug("Connect to machine with name: %s" % machine_name)

        pod = self.get_machine(lab_hash=lab_hash, machine_name=machine_name)

        if 'Running' not in pod.status.phase:
            raise Exception('Machine `%s` is not ready.' % machine_name)

        if not shell:
            shell = [Setting.get_instance().device_shell]
        else:
            shell = shlex.split(shell) if type(shell) == str else shell

        if logs and Setting.get_instance().print_startup_log:
            (result_string, _) = self.exec(lab_hash,
                                           machine_name,
                                           command="/bin/cat /var/log/shared.log /var/log/startup.log"
                                           )
            if result_string:
                print("--- Startup Commands Log\n")
                print(result_string)
                print("--- End Startup Commands Log\n")

        resp = stream(self.core_client.connect_get_namespaced_pod_exec,
                      name=pod.metadata.name,
                      namespace=lab_hash,
                      command=shell,
                      stdout=True,
                      stderr=True,
                      stdin=True,
                      tty=True,
                      _preload_content=False
                      )

        pty = KubernetesTerminal(k8s_stream=resp)
        pty.start()

    def exec(self, lab_hash, machine_name, command, tty=False, stdin=False, stdin_buffer=None, stderr=False):
        logging.debug("Executing command `%s` to machine with name: %s" % (command, machine_name))

        command = shlex.split(command) if type(command) == str else command

        try:
            # Retrieve the pod of current Deployment
            pod = self.get_machine(lab_hash=lab_hash, machine_name=machine_name)

            response = stream(self.core_client.connect_get_namespaced_pod_exec,
                              name=pod.metadata.name,
                              namespace=lab_hash,
                              command=command,
                              stdout=True,
                              stderr=stderr,
                              stdin=stdin,
                              tty=tty,
                              _preload_content=False
                              )
        except ApiException:
            return

        if stdin_buffer is None:
            stdin_buffer = []

        result = {
            'stdout': '',
            'stderr': ''
        }
        while response.is_open():
            response.update(timeout=1)
            if response.peek_stdout():
                result['stdout'] += response.read_stdout()
            if stderr and response.peek_stderr():
                result['stderr'] += response.read_stderr()
            if stdin and stdin_buffer:
                param = stdin_buffer.pop(0)
                response.write_stdin(param)
        response.close()

        return result['stdout'], result['stderr']

    def copy_files(self, deployment, path, tar_data):
        machine_name = deployment.metadata.labels["name"]
        machine_namespace = deployment.metadata.namespace

        self.exec(machine_namespace,
                  machine_name,
                  command=['tar', 'xvfz', '-', '-C', path],
                  stdin=True,
                  stdin_buffer=[tar_data]
                  )

    def get_machines_by_filters(self, lab_hash=None, machine_name=None):
        filters = ["app=kathara"]
        if machine_name:
            filters.append("name=%s" % machine_name)

        # Get all Kathara namespaces if lab_hash is None
        namespaces = list(map(lambda x: x.metadata.name, self.kubernetes_namespace.get_all())) \
            if not lab_hash else [lab_hash]

        machines = []
        for namespace in namespaces:
            machines.extend(self.core_client.list_namespaced_pod(namespace=namespace,
                                                                 label_selector=",".join(filters)
                                                                 ).items
                            )

        return machines

    def get_machine(self, lab_hash, machine_name):
        pods = self.get_machines_by_filters(lab_hash=lab_hash, machine_name=machine_name)

        logging.debug("Found pods: %s" % len(pods))

        if len(pods) != 1:
            raise Exception("Error getting the machine `%s` inside the lab." % machine_name)
        else:
            return pods[0]

    @staticmethod
    def get_deployment_name(name):
        suffix = ''
        # Underscore is replaced with -, but to keep name uniqueness append 8 chars of hash from the original name
        if '_' in name:
            suffix = '-%s' % hashlib.md5(name.encode('utf-8', errors='ignore')).hexdigest()[:8]
            name = name.replace('_', '-')

        machine_name = "%s-%s%s" % (Setting.get_instance().device_prefix, name, suffix)
        return re.sub(r'[^0-9a-z\-.]+', '', machine_name.lower())
