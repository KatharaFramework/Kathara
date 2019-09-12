import ipaddress
import os

import docker
from docker import types

from classes.setting.Setting import Setting, MAX_DOCKER_LAN_NUMBER


class DockerLinkDeployer(object):
    __slots__ = ['client', 'base_ip']

    def __init__(self, client):
        self.client = client

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

        self._configure_network(link.network_object)

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

    def _configure_network(self, network):
        """
        Privilege escalation in order to patch Docker bridges to make them behave as hubs.
        This is needed since Docker runs in a VM on Windows and MacOS.
        In order to do so, we run an alpine container with host visibility. We chroot in the host `/`.
        We patch ageing_time and group_fwd_mask of the passed network bridge.
        :param network: The Docker Network object to patch
        """
        patch_command = "/usr/sbin/chroot /host " \
                        "/bin/sh -c \"" \
                        "echo 0 > /sys/class/net/br-{net_id}/bridge/ageing_time; " \
                        "echo 65528 > /sys/class/net/br-{net_id}/bridge/group_fwd_mask" \
                        "\""

        self.client.containers.run(image="alpine",
                                   command=patch_command.format(net_id=network.id[:12]),
                                   network_mode="host",
                                   ipc_mode="host",
                                   uts_mode="host",
                                   pid_mode="host",
                                   security_opt=["seccomp=unconfined"],
                                   privileged=True,
                                   remove=True,
                                   volumes={"/": {'bind': '/host', 'mode': 'rw'}}
                                   )
