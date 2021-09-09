import io
import json
from copy import copy
from datetime import datetime
from typing import Set, Dict, Generator

from kubernetes import client
from kubernetes.client.rest import ApiException
from terminaltables import DoubleTable

from .KubernetesConfig import KubernetesConfig
from .KubernetesLink import KubernetesLink
from .KubernetesMachine import KubernetesMachine
from .KubernetesNamespace import KubernetesNamespace
from ... import utils
from ...decorators import privileged
from ...exceptions import NotSupportedError
from ...foundation.manager.IManager import IManager
from ...model.Lab import Lab
from ...model.Machine import Machine
from ...utils import pack_files_for_tar


class KubernetesManager(IManager):
    __slots__ = ['k8s_namespace', 'k8s_machine', 'k8s_link']

    def __init__(self) -> None:
        KubernetesConfig.load_kube_config()

        self.k8s_namespace: KubernetesNamespace = KubernetesNamespace()
        self.k8s_machine: KubernetesMachine = KubernetesMachine(self.k8s_namespace)
        self.k8s_link: KubernetesLink = KubernetesLink()

    def deploy_lab(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        # Kubernetes needs only lowercase letters for resources.
        # We force the hash to be lowercase
        lab.hash = lab.hash.lower()

        if selected_machines:
            lab = copy(lab)
            lab.intersect_machines(selected_machines)

        self.k8s_namespace.create(lab)
        try:
            self.k8s_link.deploy_links(lab)

            self.k8s_machine.deploy_machines(lab)
        except ApiException as e:
            if e.status == 403 and 'Forbidden' in e.reason:
                raise Exception("Previous lab execution is still terminating. Please wait.")
            else:
                raise e

    @privileged
    def update_lab(self, lab: Lab) -> None:
        raise NotSupportedError("Unable to update a running lab.")

    @privileged
    def undeploy_lab(self, lab_hash: str, selected_machines: Set[str] = None) -> None:
        lab_hash = lab_hash.lower()

        # When only some machines should be undeployed, special checks are required.
        if selected_machines:
            # Get all current deployed networks and save only their name
            networks = self.k8s_link.get_links_by_filters(lab_hash=lab_hash)
            all_networks = set([network["metadata"]["name"] for network in networks])

            # Get all current running machines (not Terminating)
            running_machines = [machine for machine in self.k8s_machine.get_machines_by_filters(lab_hash=lab_hash)
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

    @privileged
    def wipe(self, all_users: bool = False) -> None:
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag.")

        self.k8s_machine.wipe()
        self.k8s_link.wipe()

        self.k8s_namespace.wipe()

    @privileged
    def connect_tty(self, lab_hash: str, machine_name: str, shell: str = None, logs: bool = False) -> None:
        lab_hash = lab_hash.lower()

        self.k8s_machine.connect(lab_hash=lab_hash,
                                 machine_name=machine_name,
                                 shell=shell,
                                 logs=logs
                                 )

    @privileged
    def exec(self, lab_hash: str, machine_name: str, command: str) -> (str, str):
        lab_hash = lab_hash.lower()

        return self.k8s_machine.exec(lab_hash, machine_name, command, stderr=True, tty=False)

    @privileged
    def copy_files(self, machine: Machine, guest_to_host: Dict[str, io.IOBase]) -> None:
        tar_data = pack_files_for_tar(guest_to_host)

        self.k8s_machine.copy_files(machine.api_object,
                                    path="/",
                                    tar_data=tar_data
                                    )

    @privileged
    def get_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> Generator:
        if lab_hash:
            lab_hash = lab_hash.lower()

        lab_info = self.k8s_machine.get_machines_info(lab_hash=lab_hash, machine_filter=machine_name)

        return lab_info

    @privileged
    def get_formatted_lab_info(self, lab_hash: str = None, machine_name: str = None, all_users: bool = False) -> str:
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

    @privileged
    def get_machine_api_object(self, lab_hash: str, machine_name: str) -> client.V1Pod:
        return self.k8s_machine.get_machine(lab_hash, machine_name)

    @privileged
    def get_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) -> Dict[str, Any]:
        if lab_hash:
            lab_hash = lab_hash.lower()

        machine_stats = self.k8s_machine.get_machine_info(machine_name=machine_name, lab_hash=lab_hash)

        return machine_stats

    @privileged
    def get_formatted_machine_info(self, machine_name: str, lab_hash: str = None, all_users: bool = False) -> str:
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag.")

        machine_stats = self.get_machine_info(machine_name, lab_hash=lab_hash)

        machine_info = utils.format_headers("Device information") + "\n"
        machine_info += "Lab Hash: %s\n" % machine_stats["real_lab_hash"]
        machine_info += "Device Name: %s\n" % machine_stats["name"]
        machine_info += "Real Device Name: %s\n" % machine_stats["real_name"]
        machine_info += "Status: %s\n" % machine_stats["status"]
        machine_info += "Image: %s\n" % machine_stats["image"]
        machine_info += "Assigned Node: %s\n" % machine_stats["assigned_node"]
        machine_info += utils.format_headers()

        return machine_info

    @privileged
    def check_image(self, image_name: str) -> None:
        # Delegate the image check to Kubernetes
        return

    @privileged
    def get_release_version(self) -> str:
        return client.VersionApi().get_code().git_version

    @staticmethod
    def get_formatted_manager_name() -> str:
        return "Kubernetes (Megalos)"
