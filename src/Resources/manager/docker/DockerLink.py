import logging
import re
from functools import partial
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool

import docker
from docker import types

from .DockerPlugin import PLUGIN_NAME
from ... import utils
from ...model.Link import BRIDGE_LINK_NAME
from ...os.Networking import Networking
from ...setting.Setting import Setting


class DockerLink(object):
    __slots__ = ['client']

    def __init__(self, client):
        self.client = client

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

        network_ipam_config = docker.types.IPAMConfig(driver='null')

        link.api_object = self.client.networks.create(name=link_name,
                                                      driver=PLUGIN_NAME,
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
        return "kt-%s" % network.id[:12]

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
