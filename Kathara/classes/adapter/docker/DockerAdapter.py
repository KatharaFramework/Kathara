import os
from datetime import datetime

import docker

import utils
from .manager.DockerLinkManager import DockerLinkManager
from .manager.DockerMachineManager import DockerMachineManager
from ...foundation.adapter.IAdapter import IAdapter
from ...model.Link import BRIDGE_LINK_NAME


class DockerAdapter(IAdapter):
    __slots__ = ['machine_mgr', 'link_mgr', 'client']

    def __init__(self):
        self.client = docker.from_env()

        self.client.images.get_registry_data("kathara/netkit_base")

        self.machine_mgr = DockerMachineManager(self.client)
        self.link_mgr = DockerLinkManager(self.client)

    # TODO: Decorator to check if Docker is running
    def deploy_lab(self, lab, options):
        # Deploy all lab links.
        for (_, link) in lab.links.items():
            self.link_mgr.deploy(link)

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.link_mgr.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.network_object = docker_bridge

        # Deploy all lab machines.
        for (_, machine) in lab.machines.items():
            self.machine_mgr.deploy(machine,
                                    options=options,
                                    )

        for (_, machine) in lab.machines.items():
            self.machine_mgr.start(machine)

    # TODO: Decorator to check if Docker is running
    def undeploy_lab(self, lab_hash, selected_machines):
        self.machine_mgr.undeploy(lab_hash,
                                  selected_machines=selected_machines
                                  )
        self.link_mgr.undeploy(lab_hash)

    # TODO: Decorator to check if Docker is running
    def wipe(self):
        self.machine_mgr.wipe()
        self.link_mgr.wipe()

    # TODO: Decorator to check if Docker is running
    def connect_tty(self, lab_hash, machine_name, shell):
        self.machine_mgr.connect(lab_hash=lab_hash,
                                 machine_name=machine_name,
                                 shell=shell
                                 )

    def get_machine_info(self, machine_name):
        machines = self.machine_mgr.get_machines_by_filters(container_name=self.machine_mgr.get_container_name(machine_name))
        if not machines:
            raise Exception("The specified machine is not running.")

        if len(machines) > 1:
            raise Exception("There are more than one machine matching the name %d." % machine_name)

        machine = machines[0]

        machine_info = "========================= Printing info ==========================\n"

        machine_info += "Machine name: %s\n" % machine_name
        machine_info += "Image: %s\n" % machine.image.tags[0]
        machine_info += "Status: %s\n" % machine.status
        machine_info += "Lab hash: %s\n" % machine.labels['lab_hash']
        machine_info += "Real machine name: %s\n" % machine.name

        machine_stats = machine.stats(stream=False)

        machine_info += "Pids: %d\n" % machine_stats['pids_stats']['current']

        machine_info += "Cpu Usage: {0:.2f}%\n".format(machine_stats["cpu_stats"]["cpu_usage"]["total_usage"] /
                                              machine_stats["cpu_stats"]["system_cpu_usage"]
                                              )

        machine_info += "Ram Usage: " + utils.human_readable_bytes(machine_stats["memory_stats"]["usage"]) + " / " + \
                            utils.human_readable_bytes(machine_stats["memory_stats"]["limit"]) + "\n"

        net_usage_rx = 0
        net_usage_tx = 0
        for (_, stats) in machine_stats["networks"].items():
            net_usage_rx += stats["rx_bytes"]
            net_usage_tx += stats["tx_bytes"]

        net_usage = utils.human_readable_bytes(net_usage_rx) + " / " + \
                    utils.human_readable_bytes(net_usage_tx)

        machine_info += "Network Usage (DL/UL): %s\n" % net_usage

        machine_info += "================================================================="

        return machine_info

    # TODO: Decorator to check if Docker is running
    def get_info_stream(self, lab_hash=None):
        machines = self.machine_mgr.get_machines_by_filters(lab_hash=lab_hash)
        if not machines:
            raise Exception("Lab is not started.")

        machines = sorted(machines, key=lambda x: x.name)

        machine_streams = {}

        for machine in machines:
            machine_streams[machine] = machine.stats(stream=True, decode=True)

        while True:
            all_stats = "TIMESTAMP: %s\n\n" % datetime.now()
            all_stats += "LAB HASH\t\tMACHINE NAME\tCPU %\tMEM USAGE / LIMIT\tMEM %\tNET I/O\n"

            for (machine, machine_stats) in machine_streams.items():
                result = next(machine_stats)

                cpu_usage = "{0:.2f}%".format(result["cpu_stats"]["cpu_usage"]["total_usage"] /
                                              result["cpu_stats"]["system_cpu_usage"]
                                              )

                mem_usage = utils.human_readable_bytes(result["memory_stats"]["usage"]) + " / " + \
                            utils.human_readable_bytes(result["memory_stats"]["limit"])

                mem_percent = "{0:.2f}%".format((result["memory_stats"]["usage"] /
                                                 result["memory_stats"]["limit"]) * 100
                                                )

                net_usage_rx = 0
                net_usage_tx = 0
                for (_, stats) in result["networks"].items():
                    net_usage_rx += stats["rx_bytes"]
                    net_usage_tx += stats["tx_bytes"]

                net_usage = utils.human_readable_bytes(net_usage_rx) + " / " + \
                            utils.human_readable_bytes(net_usage_tx)

                all_stats += "%s\t%s\t\t%s\t%s\t%s\t%s\n" % (machine.labels['lab_hash'],
                                                             machine.labels["name"],
                                                             cpu_usage,
                                                             mem_usage,
                                                             mem_percent,
                                                             net_usage
                                                             )

            yield(all_stats)
