import ipaddress
import logging
import re
from functools import partial
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool

import docker
from docker import types

from ... import utils
from ...model.Link import BRIDGE_LINK_NAME
from ...os.Networking import Networking
from ...setting.Setting import Setting

SUBNET_DIVIDER = 16
SUBNET_MULTIPLIER = 256 * 256

SUBNET_V6_DIVIDER = 64
SUBNET_V6_MULTIPLIER = 2**64


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
        network_v4_subnet, network_v6_subnet = self._get_link_subnet()
        logging.debug("Subnet IPv4 is %s." % network_v4_subnet)

        ipv6enabled = network_v6_subnet is not None
        if ipv6enabled:
            logging.debug("Subnet IPv6 is %s." % network_v6_subnet)

        # Create the network IPAM config for Docker
        pool_configs = [
            docker.types.IPAMPool(subnet='%s' % network_v4_subnet)
        ]
        if ipv6enabled:
            pool_configs.append(docker.types.IPAMPool(subnet='%s' % network_v6_subnet))

        network_ipam_config = docker.types.IPAMConfig(driver='default',
                                                      pool_configs=pool_configs
                                                      )

        link.api_object = self.client.networks.create(name=link_name,
                                                      enable_ipv6=ipv6enabled,
                                                      driver='bridge',
                                                      check_duplicate=True,
                                                      ipam=network_ipam_config,
                                                      labels={"lab_hash": link.lab.folder_hash,
                                                              "name": link.name,
                                                              "user": utils.get_current_user_name(),
                                                              "app": "kathara",
                                                              "external": ";".join([x.get_name()
                                                                                    for x in link.external
                                                                                    ]
                                                                                   )
                                                              }
                                                      )

        if link.external:
            logging.debug("External Interfaces required, connecting them...")
            self._attach_external_interfaces(link.external, link.api_object)

    def undeploy(self, lab_hash):
        links = self.get_links_by_filters(lab_hash=lab_hash)

        cpus = cpu_count()
        links_pool = Pool(cpus)

        items = [links] if len(links) < cpus else \
                        utils.list_chunks(links, cpus)

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, True), iterable=chunk)

    def wipe(self, user=None):
        links = self.get_links_by_filters(user=user)

        cpus = cpu_count()
        links_pool = Pool(cpus)

        items = [links] if len(links) < cpus else \
                        utils.list_chunks(links, cpus)

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, False), iterable=chunk)

    def _undeploy_link(self, log, link_item):
        link_item.reload()

        if len(link_item.containers) > 0:
            return

        if log:
            logging.info("Deleting link %s." % link_item.attrs['Labels']["name"])

        self.delete_link(link_item)

    def get_docker_bridge(self):
        bridge_list = self.client.networks.list(names="bridge")
        return bridge_list.pop() if bridge_list else None

    def get_links_by_filters(self, lab_hash=None, link_name=None, user=None):
        filters = {"label": ["app=kathara"]}
        if user:
            filters["label"].append("user=%s" % user)
        if lab_hash:
            filters["label"].append("lab_hash=%s" % lab_hash)
        if link_name:
            filters["name"] = link_name

        return self.client.networks.list(filters=filters)

    def _get_link_subnet(self):
        # Get current Docker subnets
        current_v4_networks = []
        current_v6_networks = []

        for network in self.client.networks.list(filters={"driver": "bridge"}):
            ipam_config = network.attrs['IPAM']['Config']
            for ipam_net_cfg in ipam_config:
                if "Subnet" in ipam_net_cfg:
                    ipaddr = ipaddress.ip_network(ipam_net_cfg['Subnet'])
                    if type(ipaddr) is ipaddress.IPv4Network:
                        current_v4_networks.append(ipaddr)
                    else:
                        current_v6_networks.append(ipaddr)

        # If no networks are deployed, return the base IP.
        new_network4 = self.base_ip
        new_network6 = None

        if len(current_v4_networks) > 0:
            # Get last subnet defined
            last_network = max(current_v4_networks)

            # Create a /16 starting from the last Docker network
            new_network4 = ipaddress.IPv4Network("%s/%d" % (last_network.broadcast_address + 1, SUBNET_DIVIDER),
                                                strict=False
                                                )

            # If the new network overlaps the last one, add a /16 to it.
            if new_network4.overlaps(last_network):
                new_network4 = ipaddress.IPv4Network("%s/%d" % (new_network4.network_address + SUBNET_MULTIPLIER,
                                                            SUBNET_DIVIDER)
                                                    )
        
        if len(current_v6_networks) > 0:
            # Get last subnet defined
            last_network = max(current_v6_networks)

            # Create a /64 starting from the last Docker network
            new_network6 = ipaddress.IPv6Network("%s/%d" % (last_network.broadcast_address + 1, SUBNET_V6_DIVIDER),
                                                strict=False
                                                )

            # If the new network overlaps the last one, add a /64 to it.
            if new_network6.overlaps(last_network):
                new_network6 = ipaddress.IPv6Network("%s/%d" % (new_network6.network_address + SUBNET_V6_MULTIPLIER,
                                                            SUBNET_V6_DIVIDER)
                                                    )

        return new_network4, new_network6

    def configure_networks(self, links):
        """
        Patch to Docker bridges to make them act as hubs.
        We patch ageing_time and group_fwd_mask of the passed links.
        :param links: Links to patch
        """
        if not links:
            return

        patches = {
            "/sys/class/net/{br_name}/bridge/ageing_time": 0,
            "/sys/class/net/{br_name}/bridge/group_fwd_mask": 65528
        }

        def no_privilege_patch():
            logging.debug("Applying brctl patch without privilege escalation...")

            # Directly patch /sys/class opening the files
            try:
                for (_, link) in links.items():
                    if link.name == BRIDGE_LINK_NAME:
                        continue

                    for (path, value) in patches.items():
                        with open(path.format(br_name=self._get_bridge_name(link.api_object)), 'w') as sys_class:
                            sys_class.write(str(value))
            except PermissionError:
                logging.debug("Failed to patch without privilege escalation.")
                privilege_patch()

        def privilege_patch():
            logging.debug("Applying brctl patch with privilege escalation...")

            # Privilege escalation to patch bridges, since Docker runs in a VM on Windows and MacOS.
            # In order to do so, we run an alpine container with host visibility and chroot in the host `/`.
            patch_command = ["echo %d > %s" % (value, path.format(br_name=self._get_bridge_name(link.api_object)))
                             for (path, value) in patches.items() for (_, link) in links.items()
                             if link.name != BRIDGE_LINK_NAME]
            patch_command = "; ".join(patch_command)

            privilege_patch_command = "/usr/sbin/chroot /host /bin/sh -c \"%s\"" % patch_command

            # Use this only to set labels on container.
            first_link = list(links.values())[0]

            self.docker_image.check_and_pull("library/alpine")
            self.client.containers.run(image="alpine",
                                       labels=first_link.api_object.attrs['Labels'],
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
        for external_link in external_links:
            logging.info("Attaching external interface `%s` to link %s." % (external_link.get_name(),
                                                                            network.attrs['Labels']['name']
                                                                            )
                         )

            interface_index = Networking.get_or_new_interface(external_link.interface, external_link.vlan)
            Networking.attach_interface_to_bridge(interface_index, self._get_bridge_name(network))

    @staticmethod
    def _get_bridge_name(network):
        return "br-%s" % network.id[:12]

    @staticmethod
    def get_network_name(name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, utils.get_current_user_name(), name)

    @staticmethod
    def delete_link(link):
        external_label = link.attrs['Labels']["external"]
        external_links = external_label.split(";") if external_label else None

        if external_links:
            for external_link in external_links:
                logging.info("Detaching external interface `%s` from link %s." % (external_link,
                                                                                  link.attrs['Labels']['name']
                                                                                  )
                             )

                if re.search(r"^\w+\.\d+$", external_link):
                    # Only remove VLAN interfaces, physical ones cannot be removed.
                    Networking.remove_interface(external_link)

        link.remove()
