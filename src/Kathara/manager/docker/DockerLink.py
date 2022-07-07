import logging
import re
from multiprocessing.dummy import Pool
from typing import List, Union, Dict, Generator

import docker
import docker.models.networks
from docker import DockerClient
from docker import types

from .stats.DockerLinkStats import DockerLinkStats
from ..docker.DockerPlugin import PLUGIN_NAME
from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import PrivilegeError
from ...model.ExternalLink import ExternalLink
from ...model.Lab import Lab
from ...model.Link import BRIDGE_LINK_NAME, Link
from ...os.Networking import Networking
from ...setting.Setting import Setting


class DockerLink(object):
    """The class responsible for deploying Kathara collision domains as Docker networks and interact with them."""
    __slots__ = ['client']

    def __init__(self, client: DockerClient) -> None:
        self.client: DockerClient = client

    def deploy_links(self, lab: Lab, selected_links: Dict[str, Link] = None) -> None:
        """Deploy all the lab collision domains as Docker networks.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.
            selected_links (Dict[str, Link]): Keys are collision domains names, values are Link objects.

        Returns:
            None
        """
        links = selected_links.items() if selected_links else lab.links.items()

        if len(links) > 0:
            pool_size = utils.get_pool_size()
            link_pool = Pool(pool_size)

            items = utils.chunk_list(links, pool_size)

            EventDispatcher.get_instance().dispatch("links_deploy_started", items=links)

            for chunk in items:
                link_pool.map(func=self._deploy_link, iterable=chunk)

            EventDispatcher.get_instance().dispatch("links_deploy_ended")

        # Create a docker bridge link in the lab object and assign the Docker Network object associated to it.
        docker_bridge = self.get_docker_bridge()
        link = lab.get_or_new_link(BRIDGE_LINK_NAME)
        link.api_object = docker_bridge

    def _deploy_link(self, link_item: (str, Link)) -> None:
        """Deploy the collision domain contained in the link_item as a Docker network.

        Args:
            link_item (Tuple[str, Link]): A tuple composed by the name of the collision domain and a Link object

        Returns:
            None
        """
        (_, link) = link_item

        if link.name == BRIDGE_LINK_NAME:
            return

        self.create(link)

        EventDispatcher.get_instance().dispatch("link_deployed", item=link)

    def create(self, link: Link) -> None:
        """Create a Docker network representing the collision domain object and assign it to link.api_object.

        It also connect external collision domains, if present.

        Args:
            link (Kathara.model.Link.Link): A Kathara collision domain.

        Returns:
            None
        """
        # Reserved name for bridged connections, ignore.
        if link.name == BRIDGE_LINK_NAME:
            return

        # If a network with the same name exists, return it instead of creating a new one.
        link_name = self.get_network_name(link.name)
        networks = self.get_links_api_objects_by_filters(link_name=link_name)
        if networks:
            link.api_object = networks.pop()
        else:
            network_ipam_config = docker.types.IPAMConfig(driver='null')

            user_label = "shared_cd" if Setting.get_instance().shared_cd else utils.get_current_user_name()
            link.api_object = self.client.networks.create(name=link_name,
                                                          driver=PLUGIN_NAME,
                                                          check_duplicate=True,
                                                          ipam=network_ipam_config,
                                                          labels={"lab_hash": link.lab.hash,
                                                                  "name": link.name,
                                                                  "user": user_label,
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

    def undeploy(self, lab_hash: str) -> None:
        """Undeploy all the collision domains of the scenario specified by lab_hash.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.

        Returns:
            None
        """
        networks = self.get_links_api_objects_by_filters(lab_hash=lab_hash)
        for item in networks:
            item.reload()
        networks = [item for item in networks if len(item.containers) <= 0]

        if len(networks) > 0:
            pool_size = utils.get_pool_size()
            links_pool = Pool(pool_size)

            items = utils.chunk_list(networks, pool_size)

            EventDispatcher.get_instance().dispatch("links_undeploy_started", items=networks)

            for chunk in items:
                links_pool.map(func=self._undeploy_link, iterable=chunk)

            EventDispatcher.get_instance().dispatch("links_undeploy_ended")

    def wipe(self, user: str = None) -> None:
        """Undeploy all the Docker networks of the specified user. If user is None, it undeploy all the Docker networks.

        Args:
            user (str): The name of a current user on the host

        Returns:
            None
        """
        user_label = "shared_cd" if Setting.get_instance().shared_cd else user
        networks = self.get_links_api_objects_by_filters(user=user_label)
        for item in networks:
            item.reload()
        networks = [item for item in networks if len(item.containers) <= 0]

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(networks, pool_size)

        for chunk in items:
            links_pool.map(func=self._undeploy_link, iterable=chunk)

    def _undeploy_link(self, network: docker.models.networks.Network) -> None:
        """Undeploy a Docker network.

        Args:
            network (docker.models.networks.Network): The Docker network to undeploy.

        Returns:
            None
        """
        self._delete_link(network)

        EventDispatcher.get_instance().dispatch("link_undeployed", item=network)

    def get_docker_bridge(self) -> Union[None, docker.models.networks.Network]:
        """Return the Docker bridged network.

        Returns:
            Union[None, docker.models.networks.Network]: The Docker bridged network if exists, else None
        """
        bridge_list = self.client.networks.list(names="bridge")
        return bridge_list.pop() if bridge_list else None

    def get_links_api_objects_by_filters(self, lab_hash: str = None, link_name: str = None, user: str = None) -> \
            List[docker.models.networks.Network]:
        """Return the Docker networks specified by lab_hash and user.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the networks in the scenario.
            link_name (str): The name of a network. If specified, return the specified network of the scenario.
            user (str): The name of a user on the host. If specified, return only the networks of the user.

        Returns:
            List[docker.models.networks.Network]: A list of Docker networks.
        """
        filters = {"label": ["app=kathara"]}
        if user:
            filters["label"].append("user=%s" % user)
        if lab_hash:
            filters["label"].append("lab_hash=%s" % lab_hash)
        if link_name:
            filters["name"] = link_name

        return self.client.networks.list(filters=filters)

    def get_links_stats(self, lab_hash: str = None, link_name: str = None, user: str = None) -> \
            Generator[Dict[str, DockerLinkStats], None, None]:
        """Return a generator containing the Docker networks' stats.

        Args:
           lab_hash (str): The hash of a network scenario. If specified, return all the stats of the networks in the
           scenario.
           link_name (str): The name of a device. If specified, return the specified network stats.
           user (str): The name of a user on the host. If specified, return only the stats of the specified user.

        Returns:
           Generator[Dict[str, DockerMachineStats], None, None]: A generator containing network names as keys and
           DockerLinkStats as values.
        """
        networks = self.get_links_api_objects_by_filters(lab_hash=lab_hash, link_name=link_name, user=user)
        if not networks:
            if not link_name:
                raise Exception("No collision domains found.")
            else:
                raise Exception(f"Collision domains with name {link_name} not found.")

        networks = sorted(networks, key=lambda x: x.name)

        network_streams = {}

        for network in networks:
            network_streams[network.name] = DockerLinkStats(network)

        while True:
            for network_stats in network_streams.values():
                try:
                    network_stats.update()
                except StopIteration:
                    continue

            yield network_streams

    def _attach_external_interfaces(self, external_links: List[ExternalLink],
                                    network: docker.models.networks.Network) -> None:
        """Attach an external collision domain to a Docker network.

        Args:
            external_links (Kathara.model.ExternalLink): A Kathara external collision domain. It is used to create
                a collision domain attached to a host interface.
            network (docker.models.networks.Network): A Docker network.

        Returns:
            None
        """
        for external_link in external_links:
            (name, vlan) = external_link.get_name_and_vlan()

            interface_index = Networking.get_or_new_interface(external_link.interface, name, vlan)
            Networking.attach_interface_to_bridge(interface_index, self._get_bridge_name(network))

    @staticmethod
    def _get_bridge_name(network: docker.models.networks.Network) -> str:
        """Return the name of the host bridge associated to the Docker network.

        Args:
            network (docker.models.networks.Network): A Docker network.

        Returns:
            str: The name of the Docker bridge in the format "kt-<network.id[:12]>".
        """
        return "kt-%s" % network.id[:12]

    @staticmethod
    def get_network_name(name: str) -> str:
        """Return the name of a Docker network.

        Args:
            name (str): The name of a Kathara collision domain.

        Returns:
            str: The name of the Docker network in the format "|net_prefix|_|username_prefix|_|name|".
                If shared collision domains, the format is: "|net_prefix|_|lab_hash|".
        """
        username_prefix = "_%s" % utils.get_current_user_name() if not Setting.get_instance().shared_cd else ""
        return "%s%s_%s" % (Setting.get_instance().net_prefix, username_prefix, name)

    @staticmethod
    def _delete_link(network: docker.models.networks.Network) -> None:
        """Delete a Docker network.

        Args:
            network (docker.models.networks.Network): A Docker network.
        """
        external_label = network.attrs['Labels']["external"]
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

        network.remove()
