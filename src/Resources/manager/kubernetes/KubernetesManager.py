import json
from datetime import datetime

from kubernetes import client
from kubernetes.client.rest import ApiException
from terminaltables import DoubleTable

from .KubernetesConfig import KubernetesConfig
from .KubernetesLink import KubernetesLink
from .KubernetesMachine import KubernetesMachine
from .KubernetesNamespace import KubernetesNamespace
from ... import utils
from ...api.DockerHubApi import DockerHubApi
from ...decorators import privileged
from ...exceptions import NotSupportedError
from ...foundation.manager.IManager import IManager


class KubernetesManager(IManager):
    __slots__ = ['client', 'k8s_namespace', 'k8s_link', 'k8s_machine']

    # @check_k8s_status
    def __init__(self):
        KubernetesConfig.load_kube_config()
        KubernetesConfig.get_cluster_user()

        self.k8s_namespace = KubernetesNamespace()
        self.k8s_machine = KubernetesMachine(self.k8s_namespace)
        self.k8s_link = KubernetesLink()

    def deploy_lab(self, lab, privileged_mode=False):
        # Kubernetes needs only lowercase letters for resources.
        # We force the folder_hash to be lowercase
        lab.folder_hash = lab.folder_hash.lower()

        self.k8s_namespace.create(lab)
        try:
            self.k8s_link.deploy_links(lab)

            self.k8s_machine.deploy_machines(lab, privileged_mode)
        except ApiException as e:
            if e.status == 403 and 'Forbidden' in e.reason:
                raise Exception("Previous lab execution is still terminating. Please wait.")
            else:
                raise e

    @privileged
    def update_lab(self, lab_diff):
        raise NotSupportedError("Unable to update a running lab.")

    @privileged
    def undeploy_lab(self, lab_hash, selected_machines=None):
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

                if not machine.metadata.labels["name"] in selected_machines:
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
    def wipe(self, all_users=False):
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag.")

        self.k8s_machine.wipe()
        self.k8s_link.wipe()

        self.k8s_namespace.wipe()

    @privileged
    def connect_tty(self, lab_hash, machine_name, shell, logs=False):
        lab_hash = lab_hash.lower()

        self.k8s_machine.connect(lab_hash=lab_hash,
                                 machine_name=machine_name,
                                 shell=shell,
                                 logs=logs
                                 )

    @privileged
    def exec(self, lab_hash, machine_name, command):
        lab_hash = lab_hash.lower()

        return self.k8s_machine.exec(lab_hash, machine_name, command, stderr=True)

    @privileged
    def copy_files(self, machine, path, tar_data):
        self.k8s_machine.copy_files(machine.api_object,
                                    path=path,
                                    tar_data=tar_data
                                    )

    @privileged
    def get_lab_info(self, lab_hash=None, machine_name=None, all_users=False):
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag.")

        if lab_hash:
            lab_hash = lab_hash.lower()

        table_header = ["LAB HASH", "MACHINE NAME", "STATUS", "ASSIGNED NODE"]
        stats_table = DoubleTable([])
        stats_table.inner_row_border = True

        while True:
            machines = self.k8s_machine.get_machines_by_filters(lab_hash=lab_hash,
                                                                machine_name=machine_name
                                                                )

            if not machines:
                if not lab_hash:
                    raise Exception("No machines running.")
                else:
                    raise Exception("Lab is not started.")

            machines = sorted(machines, key=lambda x: x.metadata.labels["name"])

            machines_data = [
                table_header
            ]

            for machine in machines:
                machines_data.append([machine.metadata.namespace,
                                      machine.metadata.labels["name"],
                                      machine.status.phase,
                                      machine.spec.node_name
                                      ])

            stats_table.table_data = machines_data

            yield "TIMESTAMP: %s" % datetime.now() + "\n\n" + stats_table.table

    @privileged
    def get_machine_info(self, machine_name, lab_hash=None, all_users=False):
        if all_users:
            raise NotSupportedError("Cannot use `--all` flag.")

        if lab_hash:
            lab_hash = lab_hash.lower()

        machines = self.k8s_machine.get_machines_by_filters(machine_name=machine_name,
                                                            lab_hash=lab_hash
                                                            )

        if not machines:
            raise Exception("The specified machine is not running.")
        elif len(machines) > 1:
            raise Exception("There are more than one machine matching the name `%s`." % machine_name)

        machine = machines[0]

        machine_info = utils.format_headers("Machine information") + "\n"

        machine_info += "Lab Hash: %s\n" % machine.metadata.namespace
        machine_info += "Machine Name: %s\n" % machine.metadata.labels["name"]
        machine_info += "Real Machine Name: %s\n" % machine.metadata.name
        machine_info += "Status: %s\n" % machine.status.phase
        machine_info += "Image: %s\n" % machine.status.container_statuses[0].image.replace('docker.io/', '')
        machine_info += "Assigned Node: %s\n" % machine.spec.node_name

        machine_info += utils.format_headers()

        return machine_info

    @privileged
    def check_image(self, image_name):
        try:
            DockerHubApi.get_image_information(image_name)
        except Exception:
            raise Exception("Image `%s` does not exists on Docker Hub or no Internet connection." % image_name)

    @privileged
    def get_release_version(self):
        return client.VersionApi().get_code().git_version

    @staticmethod
    def get_formatted_manager_name():
        return "Kubernetes (Megalos)"
