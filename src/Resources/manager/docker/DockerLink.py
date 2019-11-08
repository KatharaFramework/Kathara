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
    __slots__ = ['client', 'docker_image', 'base_ip']

    def __init__(self, client, docker_image):
        self.client = client

        self.docker_image = docker_image

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
        logging.debug("Subnet IP is %s." % network_subnet)

        # Create the network IPAM config for Docker
        network_pool = docker.types.IPAMPool(subnet='%s' % network_subnet)

        network_ipam_config = docker.types.IPAMConfig(driver='default',
                                                      pool_configs=[network_pool]
                                                      )

        link.api_object = self.client.networks.create(name=link_name,
                                                      driver='bridge',
                                                      check_duplicate=True,
                                                      ipam=network_ipam_config,
                                                      labels={"lab_hash": link.lab.folder_hash,
                                                              "user": utils.get_current_user_name(),
                                                              "app": "kathara",
                                                              "external": ",".join([x.get_name()
                                                                                    for x in link.external
                                                                                    ]
                                                                                   )
                                                              }
                                                      )

        self._configure_network(link.api_object)
        if link.external:
            logging.debug("External Interfaces required, connecting them...")
            self._attach_external_interfaces(link.external, link.api_object)

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

        for network in self.client.networks.list(filters={"driver": "bridge"}):
            ipam_config = network.attrs['IPAM']['Config']
            first_config = ipam_config.pop()

            current_networks.append(ipaddress.ip_network(first_config['Subnet']))

        # If no networks are deployed, return the base IP.
        if not current_networks:
            return self.base_ip

        # Get last subnet defined
        last_network = max(current_networks)

        # Create a /16 starting from the last Docker network
        new_network = ipaddress.IPv4Network("%s/%d" % (last_network.broadcast_address + 1, SUBNET_DIVIDER),
                                            strict=False
                                            )

        # If the new network overlaps the last one, add a /16 to it.
        if new_network.overlaps(last_network):
            new_network = ipaddress.IPv4Network("%s/%d" % (new_network.network_address + SUBNET_MULTIPLIER,
                                                           SUBNET_DIVIDER)
                                                )

        return new_network

    def _configure_network(self, network):
        """
        Patch to Docker bridges to make them act as hubs.
        We patch ageing_time and group_fwd_mask of the passed network.
        :param network: The Docker Network object to patch
        """
        patches = {
            "/sys/class/net/{br_name}/bridge/ageing_time": 0,
            "/sys/class/net/{br_name}/bridge/group_fwd_mask": 65528
        }

        def no_privilege_patch():
            logging.debug("Applying brctl patch without privilege escalation "
                          "on network `%s`..." % network.name
                          )

            # Directly patch /sys/class opening the files
            for (path, value) in patches.items():
                try:
                    with open(path.format(br_name=self._get_bridge_name(network)), 'w') as sys_class:
                        sys_class.write(str(value))
                except PermissionError:
                    logging.debug("Failed to patch `%s`." % network.name)
                    privilege_patch()

        def privilege_patch():
            logging.debug("Applying brctl patch with privilege escalation "
                          "on network `%s`..." % network.name
                          )

            # Privilege escalation to patch bridges, since Docker runs in a VM on Windows and MacOS.
            # In order to do so, we run an alpine container with host visibility and chroot in the host `/`.
            patch_command = ["echo %d > %s" % (value, path.format(br_name=self._get_bridge_name(network)))
                             for (path, value) in patches.items()]
            patch_command = "; ".join(patch_command)
            privilege_patch_command = "/usr/sbin/chroot /host /bin/sh -c \"%s\"" % patch_command

            self.docker_image.check_and_pull("library/alpine")
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

    def _attach_external_interfaces(self, external_links, network):
        from pyroute2 import IPRoute
        ip = IPRoute()

        for external_link in external_links:
            logging.debug("Searching for interface `%s`..." % external_link.interface)

            # Search the interface
            external_link_indexes = ip.link_lookup(ifname=external_link.interface)
            # If not present, raise an error
            if not external_link_indexes:
                raise Exception("Interface `%s` not found." % external_link.interface)

            external_link_index = external_link_indexes[0]
            logging.debug("Interface found with ID = %d" % external_link_index)

            if external_link.vlan:
                external_name = external_link.get_name()

                logging.debug("VLAN Interface required... Creating `%s`..." % external_name)

                # Search the VLAN interface
                vlan_link_indexes = ip.link_lookup(ifname=external_name)

                if not vlan_link_indexes:
                    # A VLAN interface should be created before attaching it to bridge.
                    ip.link(
                        "add",
                        ifname=external_name,
                        kind="vlan",
                        link=external_link_index,
                        vlan_id=external_link.vlan
                    )

                    # Set the new interface up
                    ip.link(
                        "set",
                        index=external_link_index,
                        state="up"
                    )

                    logging.debug("Interface `%s` set UP." % external_name)

                    # Refresh the VLAN interface information
                    vlan_link_indexes = ip.link_lookup(ifname=external_name)
                    external_link_index = vlan_link_indexes[0]
                else:
                    external_link_index = vlan_link_indexes[0]

                logging.debug("Interface created with ID = %d" % external_link_index)

            # Search the bridge
            bridge_name = self._get_bridge_name(network)

            logging.debug("Attaching interface to bridge `%s`..." % bridge_name)
            bridge_index = ip.link_lookup(ifname=bridge_name)[0]

            ip.link(
                "set",
                index=external_link_index,
                master=bridge_index
            )

            logging.debug("Interface ID = %d attached to bridge %s." % (external_link_index, bridge_name))

    @staticmethod
    def _get_bridge_name(network):
        return "br-%s" % network.id[:12]

    @staticmethod
    def get_network_name(name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, utils.get_current_user_name(), name)
