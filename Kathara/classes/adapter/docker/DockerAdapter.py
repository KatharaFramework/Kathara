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

    # TODO: Decorator to check if Docker is running
    def get_info_stream(self, lab_hash):
        machines = self.machine_mgr.get_machines_by_filters(lab_hash=lab_hash)
        if not machines:
            raise Exception("Lab is not started.")

        machines = sorted(machines, key=lambda x: x.name)

        machine_streams = {}

        for machine in machines:
            machine_streams[machine] = machine.stats(stream=True, decode=True)

        while True:
            all_stats = "TIMESTAMP: %s\n\n" % datetime.now()
            all_stats += "MACHINE NAME\tCPU %\tMEM USAGE / LIMIT\tMEM %\tNET I/O\n"

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

                all_stats += "%s\t\t%s\t%s\t%s\t%s\n" % (machine.labels["name"],
                                                         cpu_usage,
                                                         mem_usage,
                                                         mem_percent,
                                                         net_usage
                                                         )

            utils.exec_by_platform(lambda: os.system('clear'), lambda: os.system('cls'), lambda: os.system('clear'))

            print(all_stats)
