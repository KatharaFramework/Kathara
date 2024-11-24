import hashlib
import json
import logging
import os
import re
import shlex
import signal
import sys
import threading
import uuid
from multiprocessing.dummy import Pool
from typing import Optional, Set, List, Union, Generator, Tuple, Dict, Any

import chardet
from kubernetes import client
from kubernetes.client.api import apps_v1_api
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from kubernetes.watch import watch

from .KubernetesConfigMap import KubernetesConfigMap
from .KubernetesNamespace import KubernetesNamespace
from .exec_stream.KubernetesExecStream import KubernetesExecStream
from .stats.KubernetesMachineStats import KubernetesMachineStats
from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import MachineAlreadyExistsError, MachineNotReadyError, MachineNotRunningError, MachineBinaryError, \
    InvocationError
from ...model.Lab import Lab
from ...model.Machine import Machine
from ...setting.Setting import Setting

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"
MAX_RESTART_COUNT = 3
MAX_TIME_ERROR = 180

OCI_RUNTIME_RE = re.compile(
    r"OCI runtime exec failed"
)

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.meta['exec_commands']
STARTUP_COMMANDS = [
    # If execution flag file is found, abort (this means that postStart has been called again)
    # If not flag the startup execution with a file
    "if [ -f \"/tmp/post_start\" ]; then exit; else touch /tmp/post_start; fi",

    "{sysctl_commands}",

    # Removes /etc/bind already existing configuration from k8s internal DNS
    "rm -Rf /etc/bind/*",

    # Unmount the /etc/resolv.conf and /etc/hosts files, automatically mounted by Kubernetes inside the container.
    # In this way, they can be overwritten by custom user files.
    "umount /etc/resolv.conf",
    "umount /etc/hosts",

    # Parse hostlab.b64 (if present)
    "if [ -f \"/tmp/kathara/hostlab.b64\" ]; then "
    "base64 -d /tmp/kathara/hostlab.b64 > /hostlab.tar.gz",
    # Extract hostlab.tar.gz data into /
    "tar xmfz /hostlab.tar.gz -C /; rm -f hostlab.tar.gz",
    "fi",

    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "(cd /hostlab/{machine_name} && tar c .) | (cd / && tar xhf - --no-same-owner --no-same-permissions); fi",

    # If /etc/hosts is not configured by the user, add the localhost mapping
    "if [ ! -s \"/etc/hosts\" ]; then "
    "echo '127.0.0.1 localhost' > /etc/hosts",
    "echo '::1 localhost' >> /etc/hosts",
    "fi",

    # Give proper permissions to /var/www
    "if [ -d \"/var/www\" ]; then "
    "chmod -R 777 /var/www/*; fi",

    # Give proper permissions to Quagga files (if present)
    "if [ -d \"/etc/quagga\" ]; then "
    "chown -R quagga:quagga /etc/quagga/",
    "chmod 640 /etc/quagga/*; fi",

    # Give proper permissions to FRR files (if present)
    "if [ -d \"/etc/frr\" ]; then "
    "chown -R frr:frr /etc/frr/",
    "chmod 640 /etc/frr/*; fi",

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
    "ip route del default dev eth0 || true",

    # Placeholder for user commands
    "{machine_commands}",

    "touch /tmp/EOS"
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
    """Class responsible for managing Kathara devices representation in Kubernetes."""
    __slots__ = ['client', 'core_client', 'kubernetes_config_map', 'kubernetes_namespace']

    def __init__(self, kubernetes_namespace: KubernetesNamespace) -> None:
        self.client: apps_v1_api.AppsV1Api = apps_v1_api.AppsV1Api()
        self.core_client: core_v1_api.CoreV1Api = core_v1_api.CoreV1Api()

        self.kubernetes_config_map: KubernetesConfigMap = KubernetesConfigMap()

        self.kubernetes_namespace: KubernetesNamespace = kubernetes_namespace

    def deploy_machines(self, lab: Lab, selected_machines: Set[str] = None, excluded_machines: Set[str] = None) -> None:
        """Deploy all the devices contained in lab.machines.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.
            selected_machines (Set[str]): A set containing the name of the devices to deploy.
            excluded_machines (Set[str]): A set containing the name of the devices to exclude.

        Returns:
            None

        Raises:
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either specify `selected_machines` or `excluded_machines`.")

        machines = lab.machines.items()
        if selected_machines:
            machines = {
                k: v for k, v in machines if k in selected_machines
            }.items()
        elif excluded_machines:
            machines = {
                k: v for k, v in machines if k not in excluded_machines
            }.items()

        if lab.general_options['privileged_machines']:
            logging.warning('Privileged option is not supported on Megalos. It will be ignored.')

        # Do not open terminals on Megalos
        Setting.get_instance().open_terminals = False

        wait_thread = threading.Thread(
            target=self._wait_machines_startup,
            args=(lab, set([k for k, _ in machines]) if selected_machines or excluded_machines else None)
        )
        wait_thread.start()

        # Deploy all lab machines.
        # If there is no lab.dep file, machines can be deployed using multithreading.
        # If not, they're started sequentially
        if not lab.has_dependencies:
            pool_size = utils.get_pool_size()
            items = utils.chunk_list(machines, pool_size)

            with Pool(pool_size) as machines_pool:
                for chunk in items:
                    machines_pool.map(func=self._deploy_machine, iterable=chunk)
        else:
            for item in machines:
                self._deploy_machine(item)

        wait_thread.join()

    def _wait_machines_startup(self, lab: Lab, selected_machines: Set[str]) -> None:
        """Wait the startup of the selected machines. Return when the selected machines become `Ready`.

        Args:
            lab (Lab): The network scenario of the devices to wait.
            selected_machines (Set[str]): A set containing the name of the devices to wait.

        Returns:
            None
        """
        machines = {k: v for (k, v) in lab.machines.items() if k in selected_machines}.items() if selected_machines \
            else lab.machines.items()

        EventDispatcher.get_instance().dispatch("machines_deploy_started", items=machines)

        machines_ready = 0
        machines_failed = 0

        # Create a timer to raise an exception if the execution gets stuck
        def raise_timeout_error():
            logging.error(
                f"Network scenario startup is not responding for over {MAX_TIME_ERROR} seconds, exiting. "
                f"To check devices status, use the following command:\n\t"
                f"kubectl -n {lab.hash} get pods"
            )

            # We should send a SIGINT to the main thread to exit the w.stream
            os.kill(os.getpid(), signal.SIGINT)

        timer = threading.Timer(MAX_TIME_ERROR, raise_timeout_error)
        timer.start()

        w = watch.Watch()
        for event in w.stream(self.kubernetes_namespace.client.list_namespaced_pod, namespace=lab.hash):
            # Every new event, cancel and create the timer
            timer.cancel()
            timer = threading.Timer(MAX_TIME_ERROR, raise_timeout_error)
            timer.start()

            machine_name = event['object'].metadata.labels['name']

            if not selected_machines or machine_name in selected_machines:
                logging.debug(f"Event: {event['type']} - Pod: {event['object'].metadata.name} (Device {machine_name})")

                if event['object'].status.container_statuses:
                    restart_count = event['object'].status.container_statuses[0].restart_count

                    if event['object'].status.container_statuses[0].ready:
                        machines_ready += 1
                        logging.debug(f"Device `{machine_name}` ready.")

                        EventDispatcher.get_instance().dispatch("machine_deployed", item=machine_name)
                    elif restart_count > 0:
                        if restart_count >= MAX_RESTART_COUNT:
                            logging.warning(
                                f"Stopping to wait device `{machine_name}` since it restarted more than "
                                f"{MAX_RESTART_COUNT} times. "
                                f"For a detailed log use the following command:\n\t"
                                f"kubectl -n {lab.hash} describe pod {event['object'].metadata.name}"
                            )

                            machines_failed += 1
                        elif event['object'].status.container_statuses[0].state.waiting and \
                                event['object'].status.container_statuses[0].state.waiting.reason == "CrashLoopBackOff":
                            logging.warning(f"Device `{machine_name}` has been restarted {restart_count} times.")

            if machines_ready + machines_failed == len(machines):
                # Finished watching, cancel the last timer
                timer.cancel()

                w.stop()

        if machines_ready == len(machines):
            EventDispatcher.get_instance().dispatch("machines_deploy_ended")

    def _deploy_machine(self, machine_item: Tuple[str, Machine]) -> None:
        """Deploy a Kubernetes deployment from the Kathara device contained in machine_item.

        Args:
           machine_item (Tuple[str, Machine]): A tuple composed by the name of the device and a device object

        Returns:
           None
        """
        (_, machine) = machine_item

        self.create(machine)

    def create(self, machine: Machine) -> None:
        """Create a Kubernetes deployment and a Pod representing the device and assign it to machine.api_object.

        Args:
            machine (Kathara.model.Machine.Machine): a Kathara device.

        Returns:
            None

        Raises:
            MachineAlreadyExistsError: If a device with the name specified already exists.
        """
        logging.debug("Creating device `%s`..." % machine.name)

        # Get the global machine metadata into a local variable (just to avoid accessing the lab object every time)
        global_machine_metadata = machine.lab.global_machine_metadata

        # If bridged is defined for the device, throw a warning.
        if "bridged" in global_machine_metadata or machine.is_bridged():
            logging.warning('Bridged option is not supported on Megalos. It will be ignored.')

        # If any ulimit is defined fot the device throw a warning
        if "ulimits" in machine.meta and len(machine.meta["ulimits"].keys()) > 0:
            logging.warning('Ulimit option is not supported on Megalos. It will be ignored.')

        # If any exec command is passed in command line, add it.
        if "exec" in global_machine_metadata:
            machine.add_meta("exec", global_machine_metadata["exec"])

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}

        sysctl_parameters["net.ipv4.ip_forward"] = 1
        sysctl_parameters["net.ipv4.icmp_ratelimit"] = 0

        if machine.is_ipv6_enabled():
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 1
            sysctl_parameters["net.ipv6.conf.all.accept_ra"] = 0
            sysctl_parameters["net.ipv6.icmp.ratelimit"] = 0
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 0
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 0
        else:
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 1
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 1
            sysctl_parameters["net.ipv6.conf.default.forwarding"] = 0
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 0

        # Merge machine sysctls
        machine.meta['sysctls'] = {**sysctl_parameters, **machine.meta['sysctls']}

        machine.add_meta('real_name', self.get_deployment_name(machine.name))

        try:
            config_map = self.kubernetes_config_map.deploy_for_machine(machine)
            machine_definition = self._build_definition(machine, config_map)

            machine.api_object = self.client.create_namespaced_deployment(body=machine_definition,
                                                                          namespace=machine.lab.hash
                                                                          )
        except ApiException as e:
            if e.status == 409 and 'Conflict' in e.reason:
                raise MachineAlreadyExistsError(machine.name)
            else:
                raise e

    def _build_definition(self, machine: Machine, config_map: client.V1ConfigMap) -> client.V1Deployment:
        """Return a Kubernetes deployment from a Kathara device and a Kubernetes ConfigMap.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.
            config_map (client.V1ConfigMap): A Kubernetes ConfigMap containing the tar data to upload on the deployment.

        Returns:
            client.V1Deployment: A Kubernetes deployment.
        """
        volume_mounts = []
        if config_map:
            # Define volume mounts for hostlab if a ConfigMap is defined.
            volume_mounts.append(client.V1VolumeMount(name="hostlab", mount_path="/tmp/kathara"))

        if Setting.get_instance().host_shared:
            volume_mounts.append(client.V1VolumeMount(name="shared", mount_path="/shared"))

        # Machine must be executed in privileged mode to run sysctls.
        security_context = client.V1SecurityContext(privileged=True)

        ports_info = machine.get_ports()
        container_ports = None
        if ports_info:
            container_ports = []
            for (host_port, protocol), guest_port in ports_info.items():
                container_ports.append(
                    client.V1ContainerPort(
                        name=str(uuid.uuid4()).replace('-', '')[0:15],
                        container_port=guest_port,
                        host_port=host_port,
                        protocol=protocol.upper()
                    )
                )

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

        shell = machine.meta["shell"] if "shell" in machine.meta else Setting.get_instance().device_shell

        # postStart lifecycle hook is launched asynchronously by k8s master when the main container is Ready
        # On Ready state, the pod has volumes and network interfaces up, so this hook is used
        # to execute custom commands coming from .startup file and "exec" option
        # Build the final startup commands string
        sysctl_commands = "; ".join(["sysctl -w -q %s=%d" % item for item in machine.meta["sysctls"].items()])
        machine_commands = "; ".join(machine.meta['exec_commands']) if machine.meta['exec_commands'] else ":"

        startup_commands_string = "; ".join(STARTUP_COMMANDS) \
            .format(machine_name=machine.name, sysctl_commands=sysctl_commands, machine_commands=machine_commands)

        post_start = client.V1LifecycleHandler(
            _exec=client.V1ExecAction(
                command=[shell, "-c", startup_commands_string]
            )
        )
        lifecycle = client.V1Lifecycle(post_start=post_start)

        env = [
            client.V1EnvVar("_MEGALOS_SHELL", shell)
        ]
        for env_var_name, env_var_value in machine.meta['envs'].items():
            env.append(client.V1EnvVar(env_var_name, env_var_value))

        container_definition = client.V1Container(
            name=machine.meta['real_name'],
            image=machine.get_image(),
            lifecycle=lifecycle,
            stdin=True,
            tty=True,
            image_pull_policy=Setting.get_instance().image_pull_policy,
            ports=container_ports,
            resources=resources,
            volume_mounts=volume_mounts,
            security_context=security_context,
            env=env
        )

        pod_annotations = {}
        network_interfaces = []
        for (idx, interface) in machine.interfaces.items():
            additional_data = {"kathara.link": interface.link.name}
            if interface.mac_address:
                additional_data["mac"] = interface.mac_address

            network_interfaces.append({
                "name": interface.link.api_object["metadata"]["name"],
                "namespace": machine.lab.hash,
                "interface": "net%d" % idx,
                **additional_data
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
                    name=config_map.metadata.name
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

        # Add Docker Config JSON for Private Registries
        image_pull_secrets = []
        if Setting.get_instance().docker_config_json:
            image_pull_secrets.append(client.V1LocalObjectReference(name='private-registry'))

        pod_spec = client.V1PodSpec(
            containers=[container_definition],
            hostname=machine.meta['real_name'],
            dns_policy="None",
            dns_config=dns_config,
            volumes=volumes,
            image_pull_secrets=image_pull_secrets
        )

        pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)
        selector_rules = client.V1LabelSelector(match_labels=pod_labels)
        deployment_spec = client.V1DeploymentSpec(replicas=1,
                                                  template=pod_template,
                                                  selector=selector_rules
                                                  )
        deployment_metadata = client.V1ObjectMeta(name=machine.meta['real_name'], labels=pod_labels)

        return client.V1Deployment(api_version="apps/v1",
                                   kind="Deployment",
                                   metadata=deployment_metadata,
                                   spec=deployment_spec
                                   )

    def undeploy(self, lab_hash: str, selected_machines: Set[str] = None, excluded_machines: Set[str] = None) -> None:
        """Undeploy all the running Kubernetes deployments and Pods contained in the scenario defined by the lab_hash.

        If selected_machines is not None, undeploy only the specified devices.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_machines (Set[str]): A set containing the name of the devices to undeploy.
            excluded_machines (Set[str]): A set containing the name of the devices to exclude.

        Returns:
            None

        Raises:
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either specify `selected_machines` or `excluded_machines`.")

        pods = self.get_machines_api_objects_by_filters(lab_hash=lab_hash)
        machines_to_watch = {item.metadata.labels["name"] for item in pods}
        if selected_machines:
            pods = [item for item in pods if item.metadata.labels["name"] in selected_machines]
            machines_to_watch = selected_machines if selected_machines else machines_to_watch
        elif excluded_machines:
            pods = [item for item in pods if item.metadata.labels["name"] not in excluded_machines]
            machines_to_watch = machines_to_watch if not excluded_machines else machines_to_watch - excluded_machines

        if len(pods) > 0:
            wait_thread = threading.Thread(target=self._wait_machines_shutdown, args=(lab_hash, machines_to_watch))
            wait_thread.start()

            pool_size = utils.get_pool_size()
            items = utils.chunk_list(pods, pool_size)

            with Pool(pool_size) as machines_pool:
                for chunk in items:
                    machines_pool.map(func=self._undeploy_machine, iterable=chunk)

            wait_thread.join()

    def _wait_machines_shutdown(self, lab_hash: str, selected_machines: Set[str]):
        """Wait the shutdown of the selected machines. Return when all the selected machines are terminated.

        Args:
            lab_hash (str): The hash of the network scenario of the devices to wait.
            selected_machines (Set[str]): A set containing the name of the devices to wait.

        Returns:
            None
        """
        EventDispatcher.get_instance().dispatch("machines_undeploy_started", items=selected_machines)

        machines_cleaned = 0

        w = watch.Watch()
        for event in w.stream(self.kubernetes_namespace.client.list_namespaced_pod, namespace=lab_hash):
            machine_name = event['object'].metadata.labels['name']

            if machine_name in selected_machines:
                logging.debug(f"Event: {event['type']} - Pod: {event['object'].metadata.name} (Device {machine_name})")

                if event['type'] == "DELETED":
                    EventDispatcher.get_instance().dispatch("machine_undeployed", item=machine_name)

                    machines_cleaned += 1

            if machines_cleaned == len(selected_machines):
                EventDispatcher.get_instance().dispatch("machines_undeploy_ended")
                w.stop()

    def wipe(self) -> None:
        """Undeploy all the running Kubernetes deployments and Pods.

        Returns:
            None
        """
        pods = self.get_machines_api_objects_by_filters()

        pool_size = utils.get_pool_size()
        items = utils.chunk_list(pods, pool_size)

        with Pool(pool_size) as machines_pool:
            for chunk in items:
                machines_pool.map(func=self._undeploy_machine, iterable=chunk)

    def _undeploy_machine(self, pod_api_object: client.V1Pod) -> None:
        """Undeploy a Kubernetes pod.

        Args:
            pod_api_object (client.V1Pod): The Kubernetes pod to undeploy.

        Returns:
            None
        """

        self._delete_machine(pod_api_object)

    def _delete_machine(self, pod_api_object: client.V1Pod) -> None:
        """Delete the Kubernetes deployment and Pod associated to pod_api_object.

        Args:
            pod_api_object (client.V1Pod): A Kubernetes Pod API object.

        Returns:
            None
        """
        machine_name = pod_api_object.metadata.labels["name"]
        machine_namespace = pod_api_object.metadata.namespace

        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=machine_name)

        try:
            shell_env_value = self.get_env_var_value_from_pod(pod_api_object, "_MEGALOS_SHELL")
            shell = shell_env_value if shell_env_value else Setting.get_instance().device_shell
            self.exec(machine_namespace, machine_name, command=[shell, '-c', shutdown_commands_string], is_stream=False)
        except ApiException:
            pass
        except MachineNotRunningError:
            pass

        deployment_name = self.get_deployment_name(machine_name)
        self.kubernetes_config_map.delete_for_machine(deployment_name, machine_namespace)
        self.client.delete_namespaced_deployment(name=deployment_name, namespace=machine_namespace)

    def connect(self, lab_hash: str, machine_name: str, shell: Union[str, List[str]] = None, logs: bool = False) \
            -> None:
        """Open a stream to the Kubernetes Pod specified by machine_name using the specified shell.

        Args:
            lab_hash (str): The hash of the network scenario containing the device.
            machine_name (str): The name of the device to connect.
            shell (Union[str, List[str]]): The path to the desired shell.
            logs (bool): If True, print the logs of the startup command.

        Returns:
            None

        Raises:
            MachineNotRunningError: If the specified device is not running.
            MachineNotReadyError: If the device is not ready.
        """
        pods = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name)
        if not pods:
            raise MachineNotRunningError(machine_name)
        deployment = pods.pop()

        if 'Running' not in deployment.status.phase:
            raise MachineNotReadyError(machine_name)

        if not shell:
            shell_env_value = self.get_env_var_value_from_pod(deployment, "_MEGALOS_SHELL")
            shell = shlex.split(shell_env_value if shell_env_value else Setting.get_instance().device_shell)
        else:
            shell = shlex.split(shell) if type(shell) is str else shell

        logging.debug("Connect to device `%s` with shell: %s" % (machine_name, shell))

        if logs and Setting.get_instance().print_startup_log:
            exec_output = self.exec(lab_hash,
                                    machine_name,
                                    command="/bin/cat /var/log/shared.log /var/log/startup.log"
                                    )
            try:
                print("--- Startup Commands Log\n")
                while True:
                    (stdout, _) = next(exec_output)

                    char_encoding = chardet.detect(stdout) if stdout else None

                    stdout = stdout.decode(char_encoding['encoding']) if stdout else ""
                    sys.stdout.write(stdout)
            except StopIteration:
                print("\n--- End Startup Commands Log\n")
                pass

        resp = stream(self.core_client.connect_get_namespaced_pod_exec,
                      name=deployment.metadata.name,
                      namespace=lab_hash,
                      command=shell,
                      stdout=True,
                      stderr=True,
                      stdin=True,
                      tty=True,
                      _preload_content=False
                      )

        from .terminal.KubernetesWSTerminal import KubernetesWSTerminal
        KubernetesWSTerminal(resp).start()

    @staticmethod
    def get_env_var_value_from_pod(pod: client.V1Pod, var_name: str) -> Optional[str]:
        """Return the value of an environment variable of the Kubernetes Pod.

        Args:
            pod (client.V1Pod): A Kubernetes Pod.
            var_name (str): The name of the environment variable.

        Returns:
            Optional[str]: The value of the environment variable.
        """
        containers = pod.spec.containers
        if not containers:
            return None

        # There is only one container definition in Megalos Pods
        container_definition = containers.pop()
        # Get env vars list
        env_vars = container_definition.env

        if not env_vars:
            return None

        # Iterate over the env vars and search the desired one
        for env_var in env_vars:
            if var_name == env_var.name:
                return env_var.value

        return None

    def exec(self, lab_hash: str, machine_name: str, command: Union[str, List], tty: bool = False, stdin: bool = False,
             stdin_buffer: List[Union[str, bytes]] = None, stderr: bool = False, is_stream: bool = True) \
            -> Union[KubernetesExecStream, Tuple[bytes, bytes, int]]:
        """Execute the command on the Kubernetes Pod specified by the lab_hash and the machine_name.

        Args:
            lab_hash (str): The hash of the network scenario containing the device.
            machine_name (str): The name of the device.
            command (Union[str, List]): The command to execute.
            tty (bool): If True, open a new tty.
            stdin (bool): If True, open the stdin channel.
            stdin_buffer (List[Union[str, bytes]]): List of command to pass to the stdin.
            stderr (bool): If True, return the stderr.
            is_stream (bool): If True, return a KubernetesExecStream object.
                If False, returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
             Union[KubernetesExecStream, Tuple[bytes, bytes, int]]: A KubernetesExecStream object or
             a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the command specified is not found on the device.
        """
        command = shlex.split(command) if type(command) is str else command

        logging.debug("Executing command `%s` to device with name: %s" % (command, machine_name))

        try:
            # Retrieve the pod of current Deployment
            pods = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name)
            if not pods:
                raise MachineNotRunningError(machine_name)
            pod = pods.pop()

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
        except ApiException as e:
            raise e

        if stdin_buffer is None:
            stdin_buffer = []

        if is_stream:
            exec_result = self._exec_stream(response, stdin, stdin_buffer, stderr)
            return KubernetesExecStream(exec_result, response)
        else:
            return self._exec_all(response, machine_name, command, stdin, stdin_buffer, stderr)

    @staticmethod
    def _exec_stream(response: Any, stdin: bool = False, stdin_buffer: List[Union[str, bytes]] = None,
                     has_stderr: bool = False) -> Generator[Tuple[bytes, bytes], None, None]:
        """Execute the command on the Kubernetes Pod, returning a generator.

        Args:
            response (Any): The stream response from Kubernetes API.
            stdin (bool): If True, open the stdin channel.
            stdin_buffer (List[Union[str, bytes]]): List of command to pass to the stdin.
            has_stderr (bool): If True, return the stderr.

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.
        """
        while response.is_open():
            stdout = None
            stderr = None
            if response.peek_stdout():
                stdout = response.read_stdout()
            if has_stderr and response.peek_stderr():
                stderr = response.read_stderr()
            if stdin and stdin_buffer:
                param = stdin_buffer.pop(0)
                response.write_stdin(param)
                if len(stdin_buffer) <= 0:
                    break

            yield stdout.encode('utf-8') if stdout else None, stderr.encode('utf-8') if stderr else None

        response.close()

    @staticmethod
    def _exec_all(response: Any, machine_name: str, command: List, stdin: bool = False,
                  stdin_buffer: List[Union[str, bytes]] = None, has_stderr: bool = False) -> Tuple[bytes, bytes, int]:
        """Execute the command on the Kubernetes Pod, returning the full output.

        Args:
            response (Any): The stream response from Kubernetes API.
            machine_name (str): The name of the device.
            command (List): The command to execute.
            stdin (bool): If True, open the stdin channel.
            stdin_buffer (List[Union[str, bytes]]): List of command to pass to the stdin.
            has_stderr (bool): If True, return the stderr.

        Returns:
            Tuple[bytes, bytes, int]: A tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            MachineBinaryError: If the command specified is not found on the device.
        """
        result = {'stdout': '', 'stderr': ''}

        while response.is_open():
            if response.peek_stdout():
                result['stdout'] += response.read_stdout()
            if has_stderr and response.peek_stderr():
                result['stderr'] += response.read_stderr()
            if stdin and stdin_buffer:
                param = stdin_buffer.pop(0)
                response.write_stdin(param)
                if len(stdin_buffer) <= 0:
                    break

        response.close()

        try:
            exit_code = response.returncode
        except ValueError as e:
            if OCI_RUNTIME_RE.search(str(e)):
                raise MachineBinaryError(shlex.join(command), machine_name)
            exit_code = 1

        return result['stdout'].encode('utf-8'), result['stderr'].encode('utf-8'), exit_code

    def copy_files(self, machine_api_object: client.V1Deployment, path: str, tar_data: bytes) -> None:
        """Copy the files contained in tar_data in the Kubernetes deployment path specified by the machine_api_object.

        Args:
            machine_api_object (client.V1Deployment): A Kubernetes deployment.
            path (str): The path of where copy the tar_data.
            tar_data (bytes): The data to copy in the deployment.

        Returns:
            None
        """
        machine_name = machine_api_object.metadata.labels["name"]
        machine_namespace = machine_api_object.metadata.namespace

        exec_output = self.exec(machine_namespace,
                                machine_name,
                                command=['tar', 'xvfz', '-', '-C', path],
                                stdin=True,
                                stdin_buffer=[tar_data]
                                )

        try:
            next(exec_output)
        except StopIteration:
            pass

    def get_machines_api_objects_by_filters(self, lab_hash: str = None, machine_name: str = None) -> List[client.V1Pod]:
        """Return the List of Kubernetes Pods.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the Kubernetes Pod in the scenario.
            machine_name (str): The name of a device. If specified, return the specified Kubernetes Pod of the scenario.

        Returns:
            List[client.V1Pod]: A list of Kubernetes Pods objects.
        """
        filters = ["app=kathara"]
        if machine_name:
            filters.append(f"name={machine_name}")

        # Get all Kathara namespaces if lab_hash is None
        namespaces = list(map(lambda x: x.metadata.name, self.kubernetes_namespace.get_all())) \
            if not lab_hash else [lab_hash]

        machines = []
        for namespace in namespaces:
            machines.extend(self.core_client.list_namespaced_pod(namespace=namespace,
                                                                 label_selector=",".join(filters),
                                                                 timeout_seconds=9999
                                                                 ).items
                            )

        return machines

    def get_machines_stats(self, lab_hash: str = None, machine_name: str = None) -> \
            Generator[Dict[str, KubernetesMachineStats], None, None]:
        """Return a generator containing the Kubernetes devices' stats.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the stats of the devices in the
                scenario.
            machine_name (str): The name of a device. If specified, return the specified device stats.

        Returns:
            Generator[Dict[str, KubernetesMachineStats], None, None]: A generator containing device name as keys and
                KubernetesMachineStats as values.
        """
        machines_stats = {}

        def load_machine_stats(pod):
            if pod.metadata.name not in machines_stats:
                machines_stats[pod.metadata.name] = KubernetesMachineStats(pod)

        while True:
            pods = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name)
            if not pods:
                yield dict()

            pool_size = utils.get_pool_size()
            items = utils.chunk_list(pods, pool_size)
            with Pool(pool_size) as machines_pool:
                for chunk in items:
                    machines_pool.map(func=load_machine_stats, iterable=chunk)

            machines_to_remove = []
            for machine_id, machine_stats in machines_stats.items():
                try:
                    machine_stats.update()
                except StopIteration:
                    machines_to_remove.append(machine_id)
                    continue

            for k in machines_to_remove:
                machines_stats.pop(k, None)

            yield machines_stats

    @staticmethod
    def get_deployment_name(name: str) -> str:
        """Return the name of the Kubernetes deployment corresponding to 'name'.

        Args:
            name (str): The name of a Kathara device.

        Returns:
            str: The name for the Kubernetes deployment.
        """
        suffix = ''
        # Underscore is replaced with -, but to keep name uniqueness append 8 chars of hash from the original name
        if '_' in name:
            suffix = '-%s' % hashlib.md5(name.encode('utf-8', errors='ignore')).hexdigest()[:8]
            name = name.replace('_', '-')

        machine_name = "%s-%s%s" % (Setting.get_instance().device_prefix, name, suffix)
        return re.sub(r'[^0-9a-z\-.]+', '', machine_name.lower())
