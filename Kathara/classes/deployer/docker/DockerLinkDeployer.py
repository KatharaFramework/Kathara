import ipaddress
import os
import utils

import docker
from docker import types

from ...model.Link import BRIDGE_LINK_NAME
from ...setting.Setting import Setting, MAX_DOCKER_LAN_NUMBER


class DockerLinkDeployer(object):
    __slots__ = ['client', 'base_ip']

    def __init__(self, client):
        self.client = client

        # Base IP subnet allocated to Kathara in Docker
        self.base_ip = u'172.19.0.0'

    def deploy(self, link):
        # Reserved name for bridged connections, ignore.
        if link.name == BRIDGE_LINK_NAME:
            return

        # If a network with the same name exists, return it instead of creating a new one.
        network_objects = self.get_links_by_filters(link_name=self.get_network_name(link.name))
        if network_objects:
            link.network_object = network_objects.pop()
            return

        network_counter = Setting.get_instance().net_counter

        # Calculate the subnet for this network.
        # Base IP + network_counter * /16
        network_subnet = ipaddress.ip_address(self.base_ip) + (network_counter * MAX_DOCKER_LAN_NUMBER)
        # Gateway is the first IP of the subnet
        network_gateway = network_subnet + 1

        # Update the network counter
        Setting.get_instance().inc_net_counter()

        # Create the network IPAM config for Docker
        network_pool = docker.types.IPAMPool(subnet='%s/16' % str(network_subnet),
                                             gateway=str(network_gateway)
                                             )

        network_ipam_config = docker.types.IPAMConfig(driver='default',
                                                      pool_configs=[network_pool]
                                                      )

        link.network_object = self.client.networks.create(name=self.get_network_name(link.name),
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

    def get_links_by_filters(self, lab_hash=None, link_name=None):
        filters = {"label": "app=kathara"}
        if lab_hash:
            filters["label"] = "lab_hash=%s" % lab_hash
        if link_name:
            filters["name"] = link_name

        return self.client.networks.list(all=True, filters=filters)

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

        # "/../" because Docker runs in a VM in Windows/MacOS.
        root_mount = utils.exec_by_platform(lambda: "/", lambda: "/../", lambda: "/../")

        self.client.containers.run(image="alpine",
                                   command=patch_command.format(net_id=network.id[:12]),
                                   network_mode="host",
                                   ipc_mode="host",
                                   uts_mode="host",
                                   pid_mode="host",
                                   security_opt=["seccomp=unconfined"],
                                   privileged=True,
                                   remove=True,
                                   volumes={root_mount: {'bind': '/host', 'mode': 'rw'}}
                                   )

    @staticmethod
    def get_network_name(name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, os.getlogin(), name)
