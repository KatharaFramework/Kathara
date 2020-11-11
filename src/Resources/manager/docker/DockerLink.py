import logging
import re
from functools import partial
from multiprocessing.dummy import Pool

import docker
import progressbar
from docker import types

from ..docker.DockerPlugin import PLUGIN_NAME
from ... import utils
from ...exceptions import PrivilegeError
from ...model.Link import BRIDGE_LINK_NAME
from ...os.Networking import Networking
from ...setting.Setting import Setting


class DockerLink(object):
    __slots__ = ['client']

    def __init__(self, client):
        self.client = client

    def deploy_links(self, lab):
        links = lab.links.items()

        if len(links) > 0:
            pool_size = utils.get_pool_size()
            link_pool = Pool(pool_size)

            items = utils.chunk_list(links, pool_size)

            progress_bar = progressbar.ProgressBar(
                widgets=['Deploying collision domains... ', progressbar.Bar(),
                         ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
                redirect_stdout=True,
                max_value=len(links)
            )

            for chunk in items:
                link_pool.map(func=partial(self._deploy_link, progress_bar), iterable=chunk)

            progress_bar.finish()

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.api_object = docker_bridge

    def _deploy_link(self, progress_bar, link_item):
        (_, link) = link_item

        if link.name == BRIDGE_LINK_NAME:
            return

        self.create(link)

        progress_bar += 1

    def create(self, link):
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
                                                              "external": ";".join([x.get_full_name()
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

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        progress_bar = progressbar.ProgressBar(
            widgets=['Deleting collision domains... ', progressbar.Bar(),
                     ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
            redirect_stdout=True,
            max_value=len(links)
        )

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, True, progress_bar), iterable=chunk)

        progress_bar.finish()

    def wipe(self, user=None):
        links = self.get_links_by_filters(user=user)

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, False, None), iterable=chunk)

    def _undeploy_link(self, log, progress_bar, link_item):
        link_item.reload()

        if len(link_item.containers) > 0:
            return

        self._delete_link(link_item)

        if log:
            progress_bar += 1

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
            (name, vlan) = external_link.get_name_and_vlan()

            interface_index = Networking.get_or_new_interface(external_link.interface, name, vlan)
            Networking.attach_interface_to_bridge(interface_index, self._get_bridge_name(network))

    @staticmethod
    def _get_bridge_name(network):
        return "kt-%s" % network.id[:12]

    @staticmethod
    def get_network_name(name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, utils.get_current_user_name(), name)

    @staticmethod
    def _delete_link(link):
        external_label = link.attrs['Labels']["external"]
        external_links = external_label.split(";") if external_label else None

        if external_links:
            for external_link in external_links:
                if re.search(r"^\w+\.\d+$", external_link):
                    if utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2):
                        if utils.is_admin():
                            # Only remove VLAN interfaces, physical ones cannot be removed.
                            Networking.remove_interface(external_link)
                        else:
                            raise PrivilegeError("You must be root in order to delete a VLAN Interface.")
                    else:
                        raise OSError("VLAN Interfaces are only available on UNIX systems.")

        link.remove()
