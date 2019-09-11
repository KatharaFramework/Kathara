import ipaddress
import os

import docker
from docker import types

from classes.setting.Setting import Setting, MAX_DOCKER_LAN_NUMBER


class DockerLinkDeployer(object):
    __slots__ = ['client', 'base_ip']

    def __init__(self):
        self.client = docker.from_env()

        # Base IP subnet allocated to Kathara in Docker
        self.base_ip = u'172.19.0.0'

    def deploy(self, link):
        if link.name == "docker_bridge":
            return

        # Get current network counter from configuration
        network_counter = Setting.get_instance().net_counter

        # Calculate the subnet for this network.
        # Base IP + network_counter * /16
        network_subnet = ipaddress.ip_address(self.base_ip) + (network_counter * MAX_DOCKER_LAN_NUMBER)
        # Gateway is the first IP of the subnet
        network_gateway = network_subnet + 1

        # Update the network counter
        Setting.get_instance().set_net_counter()

        # Create the network IPAM config for Docker
        network_pool = docker.types.IPAMPool(subnet='%s/16' % str(network_subnet),
                                             gateway=str(network_gateway)
                                             )

        network_ipam_config = docker.types.IPAMConfig(driver='default',
                                                      pool_configs=[network_pool]
                                                      )

        link.network_object = self.client.networks.create(name=self._get_network_name(link.name),
                                                          driver='bridge',
                                                          check_duplicate=True,
                                                          ipam=network_ipam_config,
                                                          labels={"lab_hash": link.lab.folder_hash,
                                                                  "app": "kathara"
                                                                  }
                                                          )

    def undeploy(self, lab_hash):
        self.client.networks.prune(filters={"label": "lab_hash=%s" % lab_hash})

    def wipe(self):
        self.client.networks.prune(filters={"label": "app=kathara"})

    def get_docker_bridge(self):
        bridge_list = self.client.networks.list(names="bridge")
        return bridge_list.pop() if bridge_list else None

    # noinspection PyMethodMayBeStatic
    def _get_network_name(self, name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, os.getlogin(), name)
