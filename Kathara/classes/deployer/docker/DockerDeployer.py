import os
from datetime import datetime

import docker

import utils
from .DockerLinkDeployer import DockerLinkDeployer
from .DockerMachineDeployer import DockerMachineDeployer
from ..IDeployer import IDeployer
from ...model.Link import BRIDGE_LINK_NAME


class DockerDeployer(IDeployer):
    __slots__ = ['machine_deployer', 'link_deployer', 'client']

    def __init__(self):
        self.client = docker.from_env()

        self.machine_deployer = DockerMachineDeployer(self.client)
        self.link_deployer = DockerLinkDeployer(self.client)

    # TODO: Decorator to check if Docker is running
    def deploy_lab(self, lab, terminals, options, xterm):
        # Deploy all lab links.
        for (_, link) in lab.links.items():
            self.link_deployer.deploy(link)

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.link_deployer.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.network_object = docker_bridge

        # Deploy all lab machines.
        for (_, machine) in lab.machines.items():
            self.machine_deployer.deploy(machine,
                                         options=options,
                                         )

        for (_, machine) in lab.machines.items():
            self.machine_deployer.start(machine,
                                        terminals=terminals,
                                        xterm=xterm
                                        )

    # TODO: Decorator to check if Docker is running
    def undeploy_lab(self, lab_hash):
        self.machine_deployer.undeploy(lab_hash)
        self.link_deployer.undeploy(lab_hash)

    # TODO: Decorator to check if Docker is running
    def wipe(self):
        self.machine_deployer.wipe()
        self.link_deployer.wipe()

    # TODO: Decorator to check if Docker is running
    def connect_tty(self, lab_hash, machine_name, command):
        self.machine_deployer.connect(lab_hash=lab_hash,
                                      machine_name=machine_name,
                                      command=command
                                      )

    # TODO: Decorator to check if Docker is running
    def get_info_stream(self, lab_hash):
        machines = self.machine_deployer.get_machines_by_filters(lab_hash=lab_hash)
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
