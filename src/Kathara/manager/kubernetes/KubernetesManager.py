import io
import json
import logging
from typing import Set, Dict, Generator, Any, List, Tuple, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from .KubernetesConfig import KubernetesConfig
from .KubernetesLink import KubernetesLink
from .KubernetesMachine import KubernetesMachine
from .KubernetesNamespace import KubernetesNamespace
from .stats.KubernetesMachineStats import KubernetesMachineStats
from ... import utils
from ...exceptions import NotSupportedError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.Machine import Machine
from ...utils import pack_files_for_tar


class KubernetesManager(IManager):
    """Class responsible for interacting with Kubernetes API."""

    __slots__ = ['k8s_namespace', 'k8s_machine', 'k8s_link']

    def __init__(self) -> None:
        KubernetesConfig.load_kube_config()

        self.k8s_namespace: KubernetesNamespace = KubernetesNamespace()
        self.k8s_machine: KubernetesMachine = KubernetesMachine(self.k8s_namespace)
        self.k8s_link: KubernetesLink = KubernetesLink(self.k8s_namespace)

    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        """Deploy a Kathara network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.
            selected_machines (Set[str]): If not None, deploy only the specified devices.

        Returns:
            None
        """
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
                raise Exception("Previous lab execution is still terminating. Please wait.")
            else:
                raise e

    def update_lab(self, lab: Lab) -> None:
        """Update a running network scenario.

        Args:
            lab (Kathara.model.Lab): A Kathara network scenario.

        Raises:
            NotSupportedError: "Unable to update a running lab."
        """
        raise NotSupportedError("Unable to update a running lab.")

    def undeploy_lab(self, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                     selected_machines: Optional[Set[str]] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (Optional[str]): The hash of the network scenario. Can be used as an alternative to lab_name.
                If None, lab_name should be set.
            lab_name (Optional[str]): The name of the network scenario. Can be used as an alternative to lab_hash.
                If None, lab_hash should be set.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.

        Returns:
            None

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
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
        self.k8s_link.undeploy(lab_hash, networks_to_delete=networks_to_delete)

        # If no machines are selected or there are no running machines, undeploy the namespace
        if not selected_machines or len(running_machines - selected_machines) <= 0:
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

        self.k8s_machine.wipe()
        self.k8s_link.wipe()

        self.k8s_namespace.wipe()

    def connect_tty(self, machine_name: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None,
                    shell: str = None, logs: bool = False) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            machine_name (str): The name of the device to connect.
            lab_hash (str): The hash of the network scenario where the device is deployed.
            lab_name (str): The name of the network scenario where the device is deployed.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.

        Returns:
            None

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)
            
        lab_hash = lab_hash.lower()

        self.k8s_machine.connect(lab_hash=lab_hash,
                                 machine_name=machine_name,
                                 shell=shell,
                                 logs=logs
                                 )

    def exec(self, machine_name: str, command: str, lab_hash: Optional[str] = None, lab_name: Optional[str] = None) -> \
            Generator[Tuple[bytes, bytes], None, None]:
        """Exec a command on a device in a running network scenario.

        Args:
            machine_name (str): The name of the device to connect.
            command (str): The command to exec on the device.
            lab_hash (Optional[str]): The hash of the network scenario where the device is deployed.
            lab_name (Optional[str]): The name of the network scenario where the device is deployed.

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.

        Raises:
            Exception: You must specify a running network scenario hash or name.
        """
        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        return self.k8s_machine.exec(lab_hash, machine_name, command, stderr=True, tty=False, is_stream=True)

    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        """Copy files on a running device in the specified paths.

        Args:
            machine (Kathara.model.Machine): A running device object. It must have the api_object field populated.
            guest_to_host (Dict[str, io.IOBase]): A dict containing the device path as key and
                fileobj to copy in path as value.

        Returns:
            None
        """
        tar_data = pack_files_for_tar(guest_to_host)

        self.k8s_machine.copy_files(machine.api_object,
                                    path="/",
                                    tar_data=tar_data
                                    )

    def get_machine_api_object(self, machine_name: str, lab_hash: str = None, lab_name: str = None,
                               all_users: bool = False) -> client.V1Pod:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            machine_name (str): The name of the device.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            If None, lab_hash should be set.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            client.V1Pod: A Kubernetes Pod.
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        pods = self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name)
        if pods:
            return pods.pop()

        raise Exception(f"Device {machine_name} not found.")

    def get_machines_api_objects(self, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> \
            List[client.V1Pod]:
        """Return API objects of running devices.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            all_users (bool): If True, return information about devices of all users.

        Returns:
            List[client.V1Pod]: Kubernetes Pod objects of devices.
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        return self.k8s_machine.get_machines_api_objects_by_filters(lab_hash=lab_hash)

    def get_link_api_object(self, link_name: str, lab_hash: str = None, lab_name: str = None,
                            all_users: bool = False) -> Any:
        """Return the corresponding API object of a collision domain in a network scenario.

        Args:
            link_name (str): The name of the collision domain.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            If None, lab_hash should be set.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            Any: Kubernetes API object of the network.
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        networks = self.k8s_link.get_links_api_objects_by_filters(lab_hash=lab_hash, link_name=link_name)
        if networks:
            return networks.pop()

        raise Exception(f"Collision Domain {link_name} not found.")

    def get_links_api_objects(self, lab_hash: str = None, lab_name: str = None, all_users: bool = False) -> \
            List[Any]:
        """Return API objects of collision domains in a network scenario.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_name.
            all_users (bool): If True, return information about collision domains of all users.

        Returns:
            List[Any]: Kubernetes API objects of networks.
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        return self.k8s_link.get_links_api_objects_by_filters(lab_hash=lab_hash)

    def get_machines_stats(self, lab_hash: str = None, lab_name: str = None, machine_name: str = None,
                           all_users: bool = False) -> Generator[Dict[str, KubernetesMachineStats], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
            machine_name (str): If specified return all the devices with machine_name.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, KubernetesMachineStats], None, None]: A generator containing dicts that has API Object
              identifier as keys and KubernetesMachineStats objects as values.
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        machines_stats = self.k8s_machine.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name)

        return machines_stats

    def get_machine_stats(self, machine_name: str, lab_hash: str = None, lab_name: str = None,
                          all_users: bool = False) -> Generator[KubernetesMachineStats, None, None]:
        """Return information of the specified device in a specified network scenario.

        Args:
            machine_name (str): The device name.
            lab_hash (str): The hash of the network scenario. Can be used as an alternative to lab_name.
            If None, lab_name should be set.
            lab_name (str): The name of the network scenario. Can be used as an alternative to lab_hash.
            If None, lab_hash should be set.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            KubernetesMachineStats: KubernetesMachineStats object containing the device info.
        """
        if all_users:
            logging.warning("User-specific options have no effect on Megalos.")

        if not lab_hash and not lab_name:
            raise Exception("You must specify a running network scenario hash or name.")

        if lab_name:
            lab_hash = utils.generate_urlsafe_hash(lab_name)

        lab_hash = lab_hash.lower()

        machines_stats = self.get_machines_stats(lab_hash=lab_hash, machine_name=machine_name)
        (_, machine_stats) = next(machines_stats).popitem()

        yield machine_stats

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
