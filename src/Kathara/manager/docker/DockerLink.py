import errno
import logging
import os
import re
from multiprocessing.dummy import Pool
from typing import Any, List, Union, Dict, Generator, Set, Optional

import docker
import docker.models.networks
from docker import DockerClient
from docker import types

from .DockerPlugin import DockerPlugin, SWITCH_MODE_OPTION
from .VdeManagement import VdeManagement, SUCCESS_CODE
from .stats.DockerLinkStats import DockerLinkStats
from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import PrivilegeError, InvocationError, DockerPluginError, LinkModeError, LinkCommandError, \
    NotSupportedError
from ...model.ExternalLink import ExternalLink
from ...model.Lab import Lab
from ...model.Link import BRIDGE_LINK_NAME, Link
from ...os.Networking import Networking
from ...setting.Setting import Setting
from ...types import SharedCollisionDomainsOption, LinkMode

# Name of the management socket of a managed collision domain, in the directory of its switch.
MANAGEMENT_SOCKET_NAME = "mgmt"
# Management commands which are refused: they stop the switch, make it read a file or end the session.
FORBIDDEN_MANAGEMENT_COMMANDS = ["shutdown", "load", "logout"]


class DockerLink(object):
    """The class responsible for deploying Kathara collision domains as Docker networks and interact with them."""
    __slots__ = ['client', 'docker_plugin']

    def __init__(self, client: DockerClient, docker_plugin: DockerPlugin) -> None:
        self.client: DockerClient = client
        self.docker_plugin: DockerPlugin = docker_plugin

    def deploy_links(self, lab: Lab, selected_links: Set[str] = None, excluded_links: Set[str] = None) -> None:
        """Deploy all the network scenario collision domains as Docker networks.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.
            selected_links (Set[str]): A set containing the name of the collision domains to deploy.
            excluded_links (Set[str]): A set containing the name of the collision domains to exclude.

        Returns:
            None

        Raises:
            InvocationError: If both `selected_links` and `excluded_links` are specified.
        """
        if selected_links and excluded_links:
            raise InvocationError(f"You can either specify `selected_links` or `excluded_links`.")

        links = lab.links.items()
        if selected_links:
            links = {
                k: v for k, v in links if k in selected_links
            }.items()
        elif excluded_links:
            links = {
                k: v for k, v in links if k not in excluded_links
            }.items()

        if len(links) > 0:
            pool_size = utils.get_pool_size()
            items = utils.chunk_list(links, pool_size)

            EventDispatcher.get_instance().dispatch("links_deploy_started", items=links)

            with Pool(pool_size) as links_pool:
                for chunk in items:
                    links_pool.map(func=self._deploy_link, iterable=chunk)

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

        It also connects external collision domains, if present.

        Args:
            link (Kathara.model.Link.Link): A Kathara collision domain.

        Returns:
            None

        Raises:
            OSError: If the link is attached to external interfaces and the host OS is not LINUX.
            PrivilegeError: If the link is attached to external interfaces and the user does not have root privileges.
            DockerPluginError: If the mode of the collision domain is not supported by the Kathara Network Plugin.
            LinkModeError: If the collision domain is already deployed with another mode.
        """
        # Reserved name for bridged connections, ignore.
        if link.name == BRIDGE_LINK_NAME:
            return

        # If a network with the same name exists, return it instead of creating a new one.
        filter_lab_hash = None
        filter_user = None
        if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED:
            filter_lab_hash = link.lab.hash
        if Setting.get_instance().shared_cds != SharedCollisionDomainsOption.USERS:
            filter_user = utils.get_current_user_name()

        networks = self.get_links_api_objects_by_filters(
            link_name=link.name, lab_hash=filter_lab_hash, user=filter_user
        )
        if networks:
            link.api_object = networks.pop()

            # A collision domain keeps the mode it is deployed with.
            deployed_mode = self.get_link_mode(link.api_object)
            if link.mode is None:
                link.mode = deployed_mode
            elif link.mode != deployed_mode:
                raise LinkModeError(
                    f"Collision domain `{link.name}` is already deployed in `{deployed_mode.value}` mode, "
                    f"it cannot be used in `{link.mode.value}` mode."
                )
        else:
            network_ipam_config = docker.types.IPAMConfig(driver='null')

            link_name = self.get_network_name(link)
            additional_labels = {}
            if Setting.get_instance().shared_cds != SharedCollisionDomainsOption.USERS:
                additional_labels["user"] = utils.get_current_user_name()
            if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED:
                additional_labels["lab_hash"] = link.lab.hash

            link.api_object = self.client.networks.create(
                name=link_name,
                driver=f"{Setting.get_instance().network_plugin}:{utils.get_architecture()}",
                check_duplicate=True,
                ipam=network_ipam_config,
                labels={
                    "name": link.name,
                    "app": "kathara",
                    "external": ";".join([x.get_full_name() for x in link.external]),
                    **additional_labels
                },
                **self._get_mode_options(link)
            )

            if link.external:
                logging.debug("External Interfaces required, connecting them...")
                self._attach_external_interfaces(link.external, link.api_object)

    def _get_mode_options(self, link: Link) -> Dict[str, Dict[str, str]]:
        """Return the arguments of the Docker network creation which set the mode of a collision domain.

        Args:
            link (Kathara.model.Link.Link): A Kathara collision domain.

        Returns:
            Dict[str, Dict[str, str]]: The `options` argument, or an empty dict for a hub (the default mode).

        Raises:
            DockerPluginError: If the mode of the collision domain is not supported by the Kathara Network Plugin.
        """
        if link.mode is None or link.mode == LinkMode.HUB:
            return {}

        if link.mode.value not in self.docker_plugin.supported_link_modes():
            raise DockerPluginError(
                f"Collision domain `{link.name}` cannot be deployed in `{link.mode.value}` mode: "
                f"the Kathara Network Plugin `{self.docker_plugin.current_name}` does not support it. "
                f"Use an up-to-date VDE version of the plugin."
            )

        return {"options": {SWITCH_MODE_OPTION: link.mode.value}}

    @staticmethod
    def get_link_mode(network: docker.models.networks.Network) -> LinkMode:
        """Return the mode of a deployed collision domain.

        Args:
            network (docker.models.networks.Network): A Docker network.

        Returns:
            Kathara.types.LinkMode: The mode of the collision domain, a hub if the network has no mode.
        """
        options = network.attrs.get("Options") or {}

        try:
            return LinkMode(options.get(SWITCH_MODE_OPTION, LinkMode.HUB.value))
        except ValueError:
            return LinkMode.HUB

    def exec(self, network: docker.models.networks.Network, command: str) -> str:
        """Run a command on the management console of a managed collision domain.

        Args:
            network (docker.models.networks.Network): The Docker network of the collision domain.
            command (str): The command, e.g. `vlan/create 10` or `port/print`.

        Returns:
            str: The text printed by the command.

        Raises:
            NotSupportedError: If the Docker daemon is not a local one on Linux.
            LinkModeError: If the collision domain is not a managed switch.
            LinkCommandError: If the command fails.
            PrivilegeError: If the user is not allowed to manage the collision domain.
            DockerPluginError: If the management console of the collision domain is not reachable.
        """
        with self._open_management(network) as management:
            return self._exec_management(management, network, command)

    def get_ports(self, network: docker.models.networks.Network) -> Dict[int, Dict[str, Any]]:
        """Return the ports of a managed collision domain.

        Args:
            network (docker.models.networks.Network): The Docker network of the collision domain.

        Returns:
            Dict[int, Dict[str, Any]]: For each port number: `vlan` (the VLAN of the untagged frames),
                `tagged_vlans` (the VLANs exchanged tagged), `active` (True when something is plugged) and
                `endpoints` (what is plugged: `<device>:eth<N>` for the interface of a device).

        Raises:
            NotSupportedError: If the Docker daemon is not a local one on Linux.
            LinkModeError: If the collision domain is not a managed switch.
            PrivilegeError: If the user is not allowed to manage the collision domain.
            DockerPluginError: If the management console of the collision domain is not reachable.
        """
        with self._open_management(network) as management:
            return VdeManagement.parse_ports(
                self._exec_management(management, network, "port/allprint"),
                self._exec_management(management, network, "vlan/allprint")
            )

    def _open_management(self, network: docker.models.networks.Network) -> VdeManagement:
        """Connect to the management console of a managed collision domain.

        Args:
            network (docker.models.networks.Network): The Docker network of the collision domain.

        Returns:
            VdeManagement: The connected client of the management console.

        Raises:
            NotSupportedError: If the Docker daemon is not a local one on Linux.
            LinkModeError: If the collision domain is not a managed switch.
            PrivilegeError: If the user is not allowed to manage the collision domain.
            DockerPluginError: If the management console of the collision domain is not reachable.
        """
        link_name = network.attrs["Labels"]["name"]

        if not (utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2)) or \
                Setting.get_instance().remote_url is not None:
            raise NotSupportedError("Collision domains can only be managed with a local Docker daemon on Linux.")

        if self.get_link_mode(network) != LinkMode.MANAGED:
            raise LinkModeError(f"Collision domain `{link_name}` is not a managed switch.")

        management = VdeManagement(
            os.path.join(self.docker_plugin.plugin_host_store_path(), self._get_bridge_name(network),
                         MANAGEMENT_SOCKET_NAME)
        )
        try:
            management.open()
        except PermissionError:
            raise PrivilegeError(f"You are not allowed to manage collision domain `{link_name}`.")
        except OSError as e:
            raise DockerPluginError(f"Unable to reach the management console of collision domain `{link_name}`: {e}")

        return management

    @staticmethod
    def _exec_management(management: VdeManagement, network: docker.models.networks.Network, command: str) -> str:
        """Run a command on an opened management console.

        Args:
            management (VdeManagement): The connected client of the management console.
            network (docker.models.networks.Network): The Docker network of the collision domain.
            command (str): The command.

        Returns:
            str: The text printed by the command.

        Raises:
            LinkCommandError: If the command fails.
        """
        link_name = network.attrs["Labels"]["name"]

        words = command.split()
        if words and words[0] in FORBIDDEN_MANAGEMENT_COMMANDS:
            raise LinkCommandError(link_name, command, SUCCESS_CODE + errno.EPERM, "Operation not permitted")

        try:
            (code, message, output) = management.exec(command)
        except ValueError as e:
            raise LinkCommandError(link_name, command, SUCCESS_CODE + errno.EINVAL, str(e))
        except OSError as e:
            raise DockerPluginError(f"Unable to reach the management console of collision domain `{link_name}`: {e}")

        if code != SUCCESS_CODE:
            raise LinkCommandError(link_name, command, code, message)

        return output

    def undeploy(self, lab_hash: str, selected_links: Optional[Set[str]] = None) -> None:
        """Undeploy all the collision domains of the scenario specified by lab_hash.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_links (Set[str]): If specified, delete only the collision domains contained in the set.

        Returns:
            None
        """
        networks = self.get_links_api_objects_by_filters(lab_hash=lab_hash)
        if selected_links is not None:
            networks = [item for item in networks if item.attrs["Labels"]["name"] in selected_links]

        for item in networks:
            item.reload()
        networks = [item for item in networks if len(item.containers) <= 0]

        if len(networks) > 0:
            pool_size = utils.get_pool_size()
            items = utils.chunk_list(networks, pool_size)

            EventDispatcher.get_instance().dispatch("links_undeploy_started", items=networks)

            with Pool(pool_size) as links_pool:
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
        user_label = user if Setting.get_instance().shared_cds != SharedCollisionDomainsOption.USERS else None
        networks = self.get_links_api_objects_by_filters(user=user_label)
        for item in networks:
            item.reload()
        networks = [item for item in networks if len(item.containers) <= 0]

        pool_size = utils.get_pool_size()
        items = utils.chunk_list(networks, pool_size)

        with Pool(pool_size) as links_pool:
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
            filters["label"].append(f"user={user}")
        if lab_hash:
            filters["label"].append(f"lab_hash={lab_hash}")
        if link_name:
            filters["label"].append(f"name={link_name}")

        return self.client.networks.list(filters=filters, greedy=True)

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

        Raises:
            PrivilegeError: If user param is None and the user does not have root privileges.
        """
        if user is None and not utils.is_admin():
            raise PrivilegeError("You must be root to get networks statistics of all users.")

        networks_stats = {}

        def load_link_stats(network):
            if network.name not in networks_stats:
                networks_stats[network.name] = DockerLinkStats(network)

        while True:
            networks = self.get_links_api_objects_by_filters(lab_hash=lab_hash, link_name=link_name, user=user)
            if not networks:
                yield dict()

            pool_size = utils.get_pool_size()
            items = utils.chunk_list(networks, pool_size)
            with Pool(pool_size) as links_pool:
                for chunk in items:
                    links_pool.map(func=load_link_stats, iterable=chunk)

            networks_to_remove = []
            for network_id, network_stats in networks_stats.items():
                try:
                    network_stats.update()
                except StopIteration:
                    networks_to_remove.append(network_id)
                    continue

            for k in networks_to_remove:
                networks_stats.pop(k, None)

            yield networks_stats

    def _delete_link(self, network: docker.models.networks.Network) -> None:
        """Delete a Docker network.

        Args:
            network (docker.models.networks.Network): A Docker network.

        Raises:
            PrivilegeError: If you are not root while deleting an external VLAN Interface.
        """
        external_label = network.attrs['Labels']["external"]
        external_links = external_label.split(";") if external_label else None

        if external_links:
            self._delete_external_interfaces(external_links, network)

        network.remove()

    def _attach_external_interfaces(self, external_links: List[ExternalLink],
                                    network: docker.models.networks.Network) -> None:
        """Attach external collision domains to a Docker network.

        Args:
            external_links (List[Kathara.model.ExternalLink]): A list of Kathara external collision domains.
                They are used to create collision domains attached to a host interface.
            network (docker.models.networks.Network): A Docker network.

        Returns:
            None

        Raises:
            OSError: If the link is attached to external interfaces and the host OS is not LINUX.
            PrivilegeError: If the link is attached to external interfaces and the user does not have root privileges.
        """
        if not (utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2)):
            raise OSError("External collision domains available only on Linux systems.")

        if not utils.is_admin():
            raise PrivilegeError("You must be root in order to use external collision domains.")

        for external_link in external_links:
            (name, vlan) = external_link.get_name_and_vlan()
            interface_index = Networking.get_or_new_interface(external_link.interface, name, vlan)
            bridge_name = self._get_bridge_name(network)

            def vde_attach():
                plugin_pid = self.docker_plugin.plugin_pid()
                switch_path = os.path.join(self.docker_plugin.plugin_store_path(), bridge_name)
                Networking.attach_interface_ns(external_link.get_full_name(), interface_index, switch_path, plugin_pid)

            def bridge_attach():
                Networking.attach_interface_bridge(interface_index, bridge_name)

            self.docker_plugin.exec_by_version(vde_attach, bridge_attach)

    def _delete_external_interfaces(self, external_links: List[str], network: docker.models.networks.Network) -> None:
        """Remove external collision domains from a Docker network.

        Args:
            external_links (List[Kathara.model.ExternalLink]): A list of Kathara external collision domains.
            network (docker.models.networks.Network): A Docker network.

        Returns:
            None

        Raises:
            OSError: If the link is attached to external interfaces and the host OS is not LINUX.
            PrivilegeError: If the link is attached to external interfaces and the user does not have root privileges.
        """
        if not (utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2)):
            raise OSError("External collision domains available only on Linux systems.")

        if not utils.is_admin():
            raise PrivilegeError("You must be root in order to use external collision domains.")

        for external_link in external_links:
            def vde_delete():
                plugin_pid = self.docker_plugin.plugin_pid()
                switch_path = os.path.join(self.docker_plugin.plugin_store_path(),
                                           self._get_bridge_name(network))
                Networking.remove_interface_ns(external_link, switch_path, plugin_pid)

            self.docker_plugin.exec_by_version(vde_delete, lambda: None)

            if re.search(r"^\w+\.\d+$", external_link):
                # Only remove VLAN interfaces, physical ones cannot be removed.
                Networking.remove_interface(external_link)

    @staticmethod
    def _get_bridge_name(network: docker.models.networks.Network) -> str:
        """Return the name of the host bridge associated to the Docker network.

        Args:
            network (docker.models.networks.Network): A Docker network.

        Returns:
            str: The name of the Docker bridge in the format "kt-<network.id[:12]>".
        """
        return f"kt-{network.id[:12]}"

    @staticmethod
    def get_network_name(link: Link) -> str:
        """Return the name of a Docker network.

        Args:
            link (Kathara.model.Link): A Kathara collision domain.

        Returns:
            str: The name of the Docker network in the format "|net_prefix|_|username_prefix|_|name|".
                If shared collision domains, the format is: "|net_prefix|_|lab_hash|".
        """
        if Setting.get_instance().shared_cds == SharedCollisionDomainsOption.LABS:
            return f"{Setting.get_instance().net_prefix}_{utils.get_current_user_name()}_{link.name}"
        elif Setting.get_instance().shared_cds == SharedCollisionDomainsOption.USERS:
            return f"{Setting.get_instance().net_prefix}_{link.name}"
        elif Setting.get_instance().shared_cds == SharedCollisionDomainsOption.NOT_SHARED:
            return f"{Setting.get_instance().net_prefix}_{utils.get_current_user_name()}_{link.name}_{link.lab.hash}"
