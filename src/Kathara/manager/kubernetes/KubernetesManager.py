import io
import json
import logging
from typing import Set, Dict, Generator, Any, List, Tuple, Optional, Union

from kubernetes import client
from kubernetes.client.rest import ApiException

from .KubernetesConfig import KubernetesConfig
from .KubernetesLink import KubernetesLink
from .KubernetesMachine import KubernetesMachine
from .KubernetesNamespace import KubernetesNamespace
from .KubernetesSecret import KubernetesSecret
from .stats.KubernetesLinkStats import KubernetesLinkStats
from .stats.KubernetesMachineStats import KubernetesMachineStats
from ... import utils
from ...exceptions import NotSupportedError, MachineNotFoundError, LinkNotFoundError, LabAlreadyExistsError, \
    InvocationError, LabNotFoundError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.Link import Link
from ...model.Machine import Machine
from ...utils import pack_files_for_tar, check_required_single_not_none_var, check_single_not_none_var


class KubernetesManager(IManager):
    """Class responsible for interacting with Kubernetes API."""

    __slots__ = ['k8s_secret', 'k8s_namespace', 'k8s_machine', 'k8s_link']

    def __init__(self) -> None:
        KubernetesConfig.load_kube_config()

        self.k8s_secret: KubernetesSecret = KubernetesSecret()
        self.k8s_namespace: KubernetesNamespace = KubernetesNamespace(self.k8s_secret)
        self.k8s_machine: KubernetesMachine = KubernetesMachine(self.k8s_namespace)
        self.k8s_link: KubernetesLink = KubernetesLink(self.k8s_namespace)

    def deploy_machine(self, machine: Machine) -> None:
        """Deploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
        """
        if not machine.lab:
            raise LabNotFoundError("Machine `%s` is not associated to a network scenario." % machine.name)

        machine.check()

        machine.lab.hash = machine.lab.hash.lower()

        self.k8s_namespace.create(machine.lab)
        self.k8s_link.deploy_links(machine.lab, selected_links={x.link.name for x in machine.interfaces.values()})
        self.k8s_machine.deploy_machines(machine.lab, selected_machines={machine.name})

    def deploy_link(self, link: Link) -> None:
        """Deploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain specified is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        link.lab.hash = link.lab.hash.lower()

        self.k8s_namespace.create(link.lab)
        self.k8s_link.deploy_links(link.lab, selected_links={link.name})

    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Set[str]): If not None, deploy only the specified devices.

        Returns:
            None

        Raises:
            NonSequentialMachineInterfaceError: If there is a missing interface number in any device of the lab.
            MachineNotFoundError: If the specified devices are not in the network scenario specified.
            LabAlreadyExistsError: If a network scenario is deployed while it is terminating its execution.
            ApiError: If the Kubernetes APIs throw an exception.
        """
        lab.check_integrity()

        if selected_machines and not lab.has_machines(selected_machines):
            machines_not_in_lab = selected_machines - set(lab.machines.keys())
            raise MachineNotFoundError(f"The following devices are not in the network scenario: {machines_not_in_lab}.")

        # Kubernetes needs only lowercase letters for resources.
        # We force the hash to be lowercase
        lab.hash = lab.hash.lower()

        selected_links = None
        if selected_machines:
            selected_links = lab.get_links_from_machines(selected_machines)

        self.k8s_namespace.create(lab)
        try:
            self.k8s_link.deploy_links(lab, selected_links=selected_links)

            self.k8s_machine.deploy_machines(lab, selected_machines=selected_machines)
        except ApiException as e:
            if e.status == 403 and 'Forbidden' in e.reason:
                raise LabAlreadyExistsError("Previous network scenario execution is still terminating. Please wait.")
            else:
                raise e

    def connect_machine_to_link(self, machine: Machine, link: Link, mac_address: Optional[str] = None) -> None:
        """Connect a Kathara device to a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): A Kathara collision domain object.
            mac_address (Optional[str]): The MAC address to assign to the interface.

        Returns:
            None

        Raises:
            NotSupportedError: Unable to update a running device on Kubernetes.
        """
        raise NotSupportedError("Unable to update a running device.")

    def disconnect_machine_from_link(self, machine: Machine, link: Link) -> None:
        """Disconnect a Kathara device from a collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.
            link (Kathara.model.Link): The Kathara collision domain from which disconnect the device.

        Returns:
            None

        Raises:
            NotSupportedError: Unable to update a running device on Kubernetes.
        """
        raise NotSupportedError("Unable to update a running device.")

    def undeploy_machine(self, machine: Machine) -> None:
        """Undeploy a Kathara device.

        Args:
            machine (Kathara.model.Machine): A Kathara machine object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified machine is not associated to a network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Machine `{machine.name}` is not associated to a network scenario.")

        machine.lab.hash = machine.lab.hash.lower()

        # Get all current running machines (not Terminating), removing the one that we're undeploying
        running_machines = [running_machine for running_machine in
                            self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=machine.lab.hash)
                            if 'Terminating' not in running_machine.status.phase and
                            running_machine.metadata.labels["name"] != machine.name]

        # From machines, save a set with all the attached networks (still needed)
        running_networks = set()
        for running_machine in running_machines:
            network_annotation = json.loads(running_machine.metadata.annotations["k8s.v1.cni.cncf.io/networks"])
            running_networks.update([net['name'] for net in network_annotation])

        # Difference between all networks of the machine to undeploy, and attached networks are the ones to delete
        machine_networks = {self.k8s_link.get_network_name(x.link.name) for x in machine.interfaces.values()}
        networks_to_delete = machine_networks - running_networks

        self.k8s_machine.undeploy(machine.lab.hash, selected_machines={machine.name})
        self.k8s_link.undeploy(machine.lab.hash, selected_links=networks_to_delete)

        if len(running_machines) <= 0:
            logging.debug("Waiting for namespace deletion...")

            self.k8s_namespace.undeploy(lab_hash=machine.lab.hash)

    def undeploy_link(self, link: Link) -> None:
        """Undeploy a Kathara collision domain.

        Args:
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            LabNotFoundError: If the collision domain specified is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError(f"Collision domain `{link.name}` is not associated to a network scenario.")

        link.lab.hash = link.lab.hash.lower()

        network_name = self.k8s_link.get_network_name(link.name)

        # Get all current running machines (not Terminating)
        running_machines = [running_machine for running_machine in
                            self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=link.lab.hash)
                            if 'Terminating' not in running_machine.status.phase]

        # From machines, save a set with all the attached networks (still needed)
        for running_machine in running_machines:
            network_annotation = json.loads(running_machine.metadata.annotations["k8s.v1.cni.cncf.io/networks"])
            # If the collision domain to undeploy is still used, do nothing
            if network_name in [net['name'] for net in network_annotation]:
                return

        self.k8s_link.undeploy(link.lab.hash, selected_links={network_name})

    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                     selected_machines: Optional[Set[str]] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        # When only some machines should be undeployed, special checks are required.
        if selected_machines:
            # Get all current deployed networks and save only their name
            networks = self.k8s_link.get_links_api_objects_by_filters(lab_hash=lab_hash)
            all_networks = set([network["metadata"]["name"] for network in networks])

            # Get all current running machines (not Terminating)
            running_machines = [machine for machine in
                                self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash)
                                if 'Terminating' not in machine.status.phase
                                ]

            # From machines, save a set with all the attached networks (still needed)
            running_networks = set()
            for machine in running_machines:
                network_annotation = json.loads(machine.metadata.annotations["k8s.v1.cni.cncf.io/networks"])
                networks = [net['name'] for net in network_annotation]

                if machine.metadata.labels["name"] not in selected_machines:
                    running_networks.update(networks)

            # Difference between all networks and attached networks are the ones to delete
            networks_to_delete = all_networks - running_networks

            # Save only the fancy name of the machines
            running_machines = set([machine.metadata.labels["name"] for machine in running_machines])
        else:
            networks_to_delete = None
            running_machines = set()

        self.k8s_machine.undeploy(lab_hash, selected_machines=selected_machines)
        self.k8s_link.undeploy(lab_hash, selected_links=networks_to_delete)

        # If no machines are selected or there are no running machines, undeploy the namespace
        if not selected_machines or len(running_machines - selected_machines) <= 0:
            logging.debug("Waiting for namespace deletion...")

            self.k8s_namespace.undeploy(lab_hash=lab_hash)

    def wipe(self, all_users: bool = False) -> None:
        """Undeploy all the running network scenarios.

        Args:
            all_users (bool): If false, undeploy only the current user network scenarios. If true, undeploy the
                running network scenarios of all users.

        Returns:
            None
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        self.k8s_secret.wipe()
        self.k8s_namespace.wipe()

    def connect_tty(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                    lab: Optional[Lab] = None, shell: str = None, logs: bool = False,
                    wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine_name (str): The name of the device to connect.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before connecting. If a tuple is provided, the first value indicates the number of retries
                before stopping waiting and the second value indicates the time interval to wait for each retry.
                Default is True.

        Returns:
            None

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        self.k8s_machine.connect(lab_hash=lab_hash,
                                 machine_name=machine_name,
                                 shell=shell,
                                 logs=logs
                                 )

    def connect_tty_obj(self, machine: Machine, shell: str = None, logs: bool = False,
                        wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine (Machine): The device to connect.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before connecting. If a tuple is provided, the first value indicates the number of retries
                before stopping waiting and the second value indicates the time interval to wait for each retry.
                Default is True.

        Returns:
            None

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        self.connect_tty(machine.name, lab=machine.lab, shell=shell, logs=logs, wait=wait)

    def exec(self, machine_name: str, command: Union[List[str], str], lab_hash: Optional[str] = None,
             lab_name: Optional[str] = None, lab: Optional[Lab] = None, wait: Union[bool, Tuple[int, float]] = False,
             stream: bool = True) -> Union[Generator[Tuple[bytes, bytes], None, None], Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine_name (str): The name of the device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
           stream (bool): If True, return a generator object containing the command output. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[Generator[Tuple[bytes, bytes]], Tuple[bytes, bytes, int]]: A generator of tuples containing the stdout
             and stderr in bytes or a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        if wait:
            logging.warning("Wait option has no effect on Megalos.")

        return self.k8s_machine.exec(lab_hash, machine_name, command, stderr=True, tty=False, is_stream=stream)

    def exec_obj(self, machine: Machine, command: Union[List[str], str], wait: Union[bool, Tuple[int, float]] = False,
                 stream: bool = True) -> Union[Generator[Tuple[bytes, bytes], None, None], Tuple[bytes, bytes, int]]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine (Machine): The device to connect.
            command (Union[List[str], str]): The command to exec on the device.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is False.
            stream (bool): If True, return a generator object containing the command output. If False,
                returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
            Union[Generator[Tuple[bytes, bytes]], Tuple[bytes, bytes, int]]: A generator of tuples containing the stdout
             and stderr in bytes or a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
        """
        if not machine.lab:
            raise LabNotFoundError(f"Device `{machine.name}` is not associated to a network scenario.")

        if wait:
            logging.warning("Wait option has no effect on Megalos.")

        return self.exec(machine.name, command, lab=machine.lab, wait=wait, stream=stream)

    def copy_files(self, machine: Machine, guest_to_host: Dict[str, Union[str, io.IOBase]]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, Union[str, io.IOBase]]): A dict containing the device path as key and a
                fileobj to copy in path as value or a path to a file.

        Returns:
            None
        """
        tar_data = pack_files_for_tar(guest_to_host)

        self.k8s_machine.copy_files(machine.api_object, path="/", tar_data=tar_data)

    def get_machine_api_object(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                               lab: Optional[Lab] = None, all_users: bool = False) -> client.V1Pod:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            machine_name (str): The name of the device.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            client.V1Pod: A Kubernetes Pod.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            MachineNotFoundError: If the device is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        pods = self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name)
        if pods:
            return pods.pop()

        raise MachineNotFoundError(f"Device {machine_name} not found.")

    def get_machines_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                                 lab: Optional[Lab] = None, all_users: bool = False) -> List[client.V1Pod]:
        """Return API objects of running devices.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            List[client.V1Pod]: Kubernetes Pod objects of devices.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower() if lab_hash else None

        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        return self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash)

    def get_link_api_object(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                            lab: Optional[Lab] = None, all_users: bool = False) -> Any:
        """Return the corresponding API object of a collision domain in a network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            Any: Kubernetes API object of the network.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
            LinkNotFoundError: If the collision domain is not found.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        networks = self.k8s_link.get_links_api_objects_by_filters(lab_hash=lab_hash, link_name=link_name)
        if networks:
            return networks.pop()

        raise LinkNotFoundError(f"Collision Domain {link_name} not found.")

    def get_links_api_objects(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                              lab: Optional[Lab] = None, all_users: bool = False) -> List[Any]:
        """Return API objects of collision domains in a network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            List[Any]: Kubernetes API objects of networks.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower() if lab_hash else None

        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        return self.k8s_link.get_links_api_objects_by_filters(lab_hash=lab_hash)

    def get_lab_from_api(self, lab_hash: str = None, lab_name: str = None) -> Lab:
        """Return the network scenario (specified by the hash or name), building it from API objects.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.

        Returns:
            Lab: The built network scenario.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        if not lab_hash and not lab_name:
            raise InvocationError("You must specify a running network scenario hash or name.")

        if lab_name:
            reconstructed_lab = Lab(lab_name)
        else:
            reconstructed_lab = Lab("reconstructed_lab")
            reconstructed_lab.hash = lab_hash

        lab_pods = self.get_machines_api_objects(lab_hash=reconstructed_lab.hash)
        lab_networks = dict(
            map(lambda x: (x['metadata']['name'], x), self.get_links_api_objects(lab_hash=reconstructed_lab.hash))
        )

        for pod in lab_pods:
            device = reconstructed_lab.get_or_new_machine(pod.metadata.labels["name"])
            device.api_object = pod

            # Rebuild device metas
            # NOTE: "privileged" and "bridged" are not supported on Megalos
            # NOTE: We cannot rebuild "sysctls", "exec", "ipv6" and "num_terms" meta.
            container = pod.spec.containers[0]
            device.add_meta("image", container.image.replace('docker.io/', ''))
            device.add_meta("shell", self.k8s_machine.get_env_var_value_from_pod(pod, "_MEGALOS_SHELL"))

            if container.resources.limits and 'memory' in container.resources.limits:
                device.add_meta("mem", container.resources.limits['memory'].upper())

            # Reconvert mcpus to a value passed by the user
            if container.resources.limits and 'cpu' in container.resources.limits:
                device.add_meta("cpu", int(container.resources.limits['cpu'].replace('m', '')) / 1000)

            for env in container.env:
                if env.name != "_MEGALOS_SHELL":
                    device.meta["envs"][env.name] = env.value

            # Reconvert ports to the device format
            if container.ports:
                for port in container.ports:
                    device.meta["ports"][(port.host_port, port.protocol.lower())] = port.container_port

            for network_conf in json.loads(pod.metadata.annotations["k8s.v1.cni.cncf.io/networks"]):
                network = lab_networks[network_conf['name']]
                link = reconstructed_lab.get_or_new_link(network['metadata']['labels']['name'])
                link.api_object = network

                iface_mac_addr = None
                if "mac" in network_conf:
                    iface_mac_addr = network_conf['mac']

                device.add_interface(link, mac_address=iface_mac_addr)

        return reconstructed_lab

    def update_lab_from_api(self, lab: Lab) -> None:
        """Update the passed network scenario from API objects.

        Args:
            lab (Lab): The network scenario to update.

        Raises:
            NotSupportedError: Unable to update a running network scenario on Kubernetes.
        """
        raise NotSupportedError("Unable to update a running network scenario.")

    def get_machines_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                           lab: Optional[Lab] = None, machine_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, KubernetesMachineStats], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
            machine_name (str): If specified return all the devices with machine_name.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, KubernetesMachineStats], None, None]: A generator containing dicts that has API Object
                identifier as keys and KubernetesMachineStats objects as values.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower() if lab_hash else None

        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        return self.k8s_machine.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name)

    def get_machine_stats(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                          lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[KubernetesMachineStats], None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine_name (str): The name of the device for which statistics are requested.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[Optional[KubernetesMachineStats], None, None]: A generator containing the KubernetesMachineStats
            object with the device info. Returns None if the device is not found.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        machines_stats = self.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name)
        machines_stats_next = next(machines_stats)
        if machines_stats_next:
            (_, machine_stats) = machines_stats_next.popitem()
            yield machine_stats
        else:
            yield None

    def get_machine_stats_obj(self, machine: Machine, all_users: bool = False) \
            -> Generator[Optional[KubernetesMachineStats], None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine (Machine): The device for which statistics are requested.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            Generator[Optional[IMachineStats], None, None]: A generator containing the IMachineStats object
            with the device info. Returns None if the device is not found.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
            MachineNotRunningError: If the specified device is not running.
        """
        if not machine.lab:
            raise LabNotFoundError("Device `%s` is not associated to a network scenario." % machine.name)

        return self.get_machine_stats(machine.name, lab=machine.lab, all_users=all_users)

    def get_links_stats(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None, lab: Optional[Lab] = None,
                        link_name: str = None, all_users: bool = False) \
            -> Generator[Dict[str, KubernetesLinkStats], None, None]:
        """Return information about deployed networks.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name.
           link_name (str): If specified return all the networks with link_name.
           all_users (bool): If True, return information about the networks of all users.

        Returns:
             Generator[Dict[str, KubernetesLinkStats], None, None]: A generator containing dicts that has API Object
                identifier as keys and KubernetesLinkStats objects as values.
        """
        check_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower() if lab_hash else None

        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        return self.k8s_link.get_links_stats(lab_hash=lab_hash, link_name=link_name)

    def get_link_stats(self, link_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                       lab: Optional[Lab] = None, all_users: bool = False) \
            -> Generator[Optional[KubernetesLinkStats], None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link_name (str): The name of the collision domain for which statistics are requested.
            lab_hash (Optional[str]): The hash of the network scenario.
                Can be used as an alternative to lab_name and lab. If None, lab_name or lab should be set.
            lab_name (Optional[str]): The name of the network scenario.
                Can be used as an alternative to lab_hash and lab. If None, lab_hash or lab should be set.
            lab (Optional[Kathara.model.Lab]): The network scenario object.
                Can be used as an alternative to lab_hash and lab_name. If None, lab_hash or lab_name should be set.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
            Generator[Optional[KubernetesLinkStats], None, None]: A generator containing the KubernetesLinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            InvocationError: If a running network scenario hash or name is not specified.
        """
        check_required_single_not_none_var(lab_hash=lab_hash, lab_name=lab_name, lab=lab)
        if lab:
            lab_hash = lab.hash
        elif lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        links_stats = self.get_links_stats(lab_hash=lab_hash, link_name=link_name, all_users=all_users)
        links_stats_next = next(links_stats)
        if links_stats_next:
            (_, link_stats) = links_stats_next.popitem()
            yield link_stats
        else:
            yield None

    def get_link_stats_obj(self, link: Link, all_users: bool = False) \
            -> Generator[Optional[KubernetesLinkStats], None, None]:
        """Return information of the specified deployed network in a specified network scenario.

        Args:
            link (Link): The collision domain for which statistics are requested.
            all_users (bool): If True, return information about the networks of all users.

        Returns:
            Generator[Optional[ILinkStats], None, None]: A generator containing the ILinkStats object
            with the network info. Returns None if the network is not found.

        Raises:
            LabNotFoundError: If the specified device is not associated to any network scenario.
        """
        if not link.lab:
            raise LabNotFoundError(f"Link `{link.name}` is not associated to a network scenario.")

        return self.get_link_stats(link.name, lab=link.lab, all_users=all_users)

    def check_image(self, image_name: str) -> None:
        """Useless. The Check of the image is delegated to Kubernetes.

        Args:
            image_name (str): The name of the image

        Returns:
            None
        """
        # Delegate the image check to Kubernetes
        return

    def get_release_version(self) -> str:
        """Return the current manager version.

        Returns:
            str: The current manager version.
        """
        return client.VersionApi().get_code().git_version

    @staticmethod
    def get_formatted_manager_name() -> str:
        """Return a formatted string containing the current manager name.

        Returns:
            str: A formatted string containing the current manager name.
        """
        return "Kubernetes (Megalos)"
