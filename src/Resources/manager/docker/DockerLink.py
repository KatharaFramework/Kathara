import ipaddress
import logging

import docker
from docker import types

from ... import utils
from ...model.Link import BRIDGE_LINK_NAME
from ...setting.Setting import Setting

SUBNET_DIVIDER = 16
SUBNET_MULTIPLIER = 256 * 256


class DockerLink(object):
    __slots__ = ['client', 'base_ip']

    def __init__(self, client):
        self.client = client

        # Base IP subnet allocated to Kathara in Docker
        self.base_ip = ipaddress.ip_address(u'172.19.0.0')

    def deploy(self, link):
        # Reserved name for bridged connections, ignore.
        if link.name == BRIDGE_LINK_NAME:
            return

        # If a network with the same name exists, return it instead of creating a new one.
        link_name = self.get_network_name(link.name)
        network_objects = self.get_links_by_filters(link_name=link_name)
        if network_objects:
            link.api_object = network_objects.pop()
            return

        logging.debug("Creating subnet for link `%s`..." % link.name)
        network_subnet = self._get_link_subnet()
        logging.debug("Subnet IP is %s/%d." % (network_subnet, SUBNET_DIVIDER))

        # Gateway is the first IP of the subnet
        network_gateway = network_subnet + 1

        # Create the network IPAM config for Docker
        network_pool = docker.types.IPAMPool(subnet='%s/%d' % (str(network_subnet), SUBNET_DIVIDER),
                                             gateway=str(network_gateway)
                                             )

        network_ipam_config = docker.types.IPAMConfig(driver='default',
                                                      pool_configs=[network_pool]
                                                      )

        link.api_object = self.client.networks.create(name=link_name,
                                                      driver='bridge',
                                                      check_duplicate=True,
                                                      ipam=network_ipam_config,
                                                      labels={"lab_hash": link.lab.folder_hash,
                                                              "user": utils.get_current_user_name(),
                                                              "app": "kathara"
                                                              }
                                                      )

        self._configure_network(link.api_object)

    def undeploy(self, lab_hash):
        self.client.networks.prune(filters={"label": "lab_hash=%s" % lab_hash})

    def wipe(self, user=None):
        filters = {"label": "app=kathara"}
        if user:
            filters["label"] = "user=%s" % user

        self.client.networks.prune(filters=filters)

    def get_docker_bridge(self):
        bridge_list = self.client.networks.list(names="bridge")
        return bridge_list.pop() if bridge_list else None

    def get_links_by_filters(self, lab_hash=None, link_name=None):
        filters = {"label": "app=kathara"}
        if lab_hash:
            filters["label"] = "lab_hash=%s" % lab_hash
        if link_name:
            filters["name"] = link_name

        return self.client.networks.list(filters=filters)

    def _get_link_subnet(self):
        # Get current Docker subnets
        current_networks = []
        for network in self.get_links_by_filters():
            ipam_config = network.attrs['IPAM']['Config']
            first_config = ipam_config.pop()

            current_networks.append(ipaddress.ip_network(first_config['Subnet']))

        # If no networks are deployed, return the base IP.
        if not current_networks:
            return self.base_ip

        # Get last subnet defined
        last_network = max(current_networks)

        # Calculate a new subnet by adding a /16 to the last deployed subnet.
        return last_network.network_address + SUBNET_MULTIPLIER

    def _configure_network(self, network):
        """
        Patch to Docker bridges to make them act as hubs.
        We patch ageing_time and group_fwd_mask of the passed network.
        :param network: The Docker Network object to patch
        """
        patches = {
            "/sys/class/net/br-{net_id}/bridge/ageing_time": 0,
            "/sys/class/net/br-{net_id}/bridge/group_fwd_mask": 65528
        }

        def no_privilege_patch():
            # Directly patch /sys/class opening the files
            for (path, value) in patches.items():
                try:
                    with open(path.format(net_id=network.id[:12]), 'w') as sys_class:
                        sys_class.write(str(value))
                except PermissionError:
                    privilege_patch()

        def privilege_patch():
            # Privilege escalation to patch bridges, since Docker runs in a VM on Windows and MacOS.
            # In order to do so, we run an alpine container with host visibility and chroot in the host `/`.
            patch_command = ["echo %d > %s" % (value, path.format(net_id=network.id[:12]))
                             for (path, value) in patches.items()]
            patch_command = "; ".join(patch_command)
            privilege_patch_command = "/usr/sbin/chroot /host /bin/sh -c \"%s\"" % patch_command

            self.client.containers.run(image="alpine",
                                       command=privilege_patch_command,
                                       network_mode="host",
                                       ipc_mode="host",
                                       uts_mode="host",
                                       pid_mode="host",
                                       security_opt=["seccomp=unconfined"],
                                       privileged=True,
                                       remove=True,
                                       # "/../" because runs in a VM, so root is one level above
                                       volumes={"/../": {'bind': '/host', 'mode': 'rw'}}
                                       )

        utils.exec_by_platform(no_privilege_patch, privilege_patch, privilege_patch)

    @staticmethod
    def get_network_name(name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, utils.get_current_user_name(), name)
