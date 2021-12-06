import io
import json
from datetime import datetime
from typing import Set, Dict, Generator, Any, List, Tuple

from kubernetes import client
from kubernetes.client.rest import ApiException
from terminaltables import DoubleTable

from .KubernetesConfig import KubernetesConfig
from .KubernetesLink import KubernetesLink
from .KubernetesMachine import KubernetesMachine
from .KubernetesNamespace import KubernetesNamespace
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
        self.k8s_link: KubernetesLink = KubernetesLink()

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

    def undeploy_lab(self, lab_hash: str, selected_machines: Set[str] = None) -> None:
        """Undeploy a Kathara network scenario.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_machines (Set[str]): If not None, undeploy only the specified devices.

        Returns:
            None
        """
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
            raise NotSupportedError("Cannot use `--all` flag.")

        self.k8s_machine.wipe()
        self.k8s_link.wipe()

        self.k8s_namespace.wipe()

    def connect_tty(self, lab_hash: str, machine_name: str, shell: str = None, logs: bool = False) -> None:
        """Connect to a device in a running network scenario, using the specified shell.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            machine_name (str): The name of the device to connect.
            shell (str): The name of the shell to use for connecting.
            logs (bool): If True, print startup logs on stdout.

        Returns:
            None
        """
        lab_hash = lab_hash.lower()

        self.k8s_machine.connect(lab_hash=lab_hash,
                                 machine_name=machine_name,
                                 shell=shell,
                                 logs=logs
                                 )

    def exec(self, lab_hash: str, machine_name: str, command: str) -> Generator[Tuple[bytes, bytes], None, None]:
        """Exec a command on a device in a running network scenario.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            machine_name (str): The name of the device to connect.
            command (str): The command to exec on the device

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.
        """
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

    def get_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> \
            Generator[Dict[str, Any], None, None]:
        """Return information about the running devices.

        Args:
            lab_hash (str): If not None, return information of the corresponding network scenario.
            machine_name (str): If not None, return information of the specified device.
            all_users (bool): If True, return information about the device of all users.

        Returns:
              Generator[Dict[str, Any], None, None]: A generator containing dicts containing device names as keys and
              their info as values.
        """
        if lab_hash:
            lab_hash = lab_hash.lower()

        lab_info = self.k8s_machine.get_machines_info(lab_hash=lab_hash, machine_name=machine_name)

        return lab_info

    def get_formatted_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> str:
        """Return a formatted string with the information about the running devices.

        Args:
            lab_hash (str): If not None, return information of the corresponding network scenario.
            machine_name (str): If not None, return information of the specified device.
            all_users (bool): If True, return information about the device of all users.

        Returns:
             str: String containing devices info
        """
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag on Megalos.")

        table_header = ["LAB HASH", "DEVICE NAME", "STATUS", "ASSIGNED NODE"]
        stats_table = DoubleTable([])
        stats_table.inner_row_border = True

        lab_info = self.get_lab_info(lab_hash=lab_hash, machine_name=machine_name)

        while True:
            machines_data = [
                table_header
            ]

            try:
                result = next(lab_info)
            except StopIteration:
                return

            if not result:
                return

            for machine_stats in result:
                machines_data.append([machine_stats["real_lab_hash"],
                                      machine_stats["name"],
                                      machine_stats["status"],
                                      machine_stats["assigned_node"]
                                      ])

            stats_table.table_data = machines_data

            yield "TIMESTAMP: %s" % datetime.now() + "\n\n" + stats_table.table

    def get_machine_api_object(self, lab_hash: str, machine_name: str) -> client.V1Pod:
        """Return the corresponding API object of a running device in a network scenario.

        Args:
            lab_hash (str): The hash of the network scenario.
            machine_name (str): The name of the device.

        Returns:
            client.V1Pod: A Kubernetes PoD.
        """
        lab_hash = lab_hash.lower()
        return self.k8s_machine.get_machine_api_object(lab_hash, machine_name)

    def get_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) \
            -> List[Dict[str, Any]]:
        """Return information of running devices with a specified name.

        Args:
            machine_name (str): The device name.
            lab_hash (str): If not None, search the device in the specified network scenario.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            List[Dict[str, Any]]: A list of dicts containing the devices info.
        """
        if lab_hash:
            lab_hash = lab_hash.lower()

        machine_stats = self.k8s_machine.get_machine_info(machine_name=machine_name, lab_hash=lab_hash)

        return machine_stats

    def get_formatted_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) -> str:
        """Return formatted information of running devices with a specified name.

        Args:
            machine_name (str): The device name.
            lab_hash (str): If not None, search the device in the specified network scenario.
            all_users (bool): If True, search the device among all the users devices.

        Returns:
            str: The formatted devices properties.
        """
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag.")

        machines_stats = self.get_machine_info(machine_name, lab_hash=lab_hash)

        machines_info = []

        for machine_stats in machines_stats:
            machine_info = utils.format_headers("Device information") + "\n"
            machine_info += "Lab Hash: %s\n" % machine_stats["real_lab_hash"]
            machine_info += "Device Name: %s\n" % machine_stats["name"]
            machine_info += "Real Device Name: %s\n" % machine_stats["real_name"]
            machine_info += "Status: %s\n" % machine_stats["status"]
            machine_info += "Image: %s\n" % machine_stats["image"]
            machine_info += "Assigned Node: %s\n" % machine_stats["assigned_node"]
            machine_info += utils.format_headers()

            machines_info.append(machine_info)

        return "\n\n".join(machines_info)

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
