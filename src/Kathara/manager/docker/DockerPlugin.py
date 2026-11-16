import json
import logging
import os.path
from typing import Callable, Any, Dict, Optional, Set

from docker import DockerClient
from docker.errors import NotFound
from docker.models.plugins import Plugin

from ... import utils
from ...exceptions import DockerPluginError
from ...os.Networking import Networking
from ...setting.Setting import Setting
from ...types import CollisionDomainTypesOption

LINUX_PLUGIN_NAME = "kathara/katharanp"
VDE_PLUGIN_NAME = "kathara/katharanp_vde"
P2P_PLUGIN_NAME = "kathara/katharanp_p2p"

HOSTTMP_KEY = "tmp"
XTABLES_CONFIGURATION_KEY = "xtables_lock"
XTABLES_LOCK_PATH = "/run/xtables.lock"

LINK_TYPE_TO_PLUGIN = {
    CollisionDomainTypesOption.BRIDGE: LINUX_PLUGIN_NAME,
    CollisionDomainTypesOption.HUB: VDE_PLUGIN_NAME,
    CollisionDomainTypesOption.P2P: P2P_PLUGIN_NAME
}


class DockerPlugin(object):
    """Class responsible for interacting with Docker Plugins."""
    __slots__ = ['_default_name', 'client']

    PLUGIN_STATE_PATH = "/run/docker/runtime-runc/plugins.moby/{id}/state.json"

    def __init__(self, client: DockerClient):
        self._default_name: str = f"{Setting.get_instance().network_plugin}:{utils.get_architecture()}"
        self.client: DockerClient = client

    def check_from_list(self, plugins: Set[str]) -> None:
        """Check a list of specified plugins.

        Args:
            plugins (Set[str]): A set of plugin names to check.

        Returns:
            None

        Raises:
            DockerPluginError: If the Kathara Network Plugin is not found on remote Docker connection.
            DockerPluginError: If the Kathara Network Plugin is not enabled on remote Docker connection.
        """
        for plugin in plugins:
            self._check_and_download(plugin)

    def _check_and_download(self, plugin_name: str) -> None:
        """Check the presence of the specified Kathara Network Plugin and download it or upgrade it, if needed.

        Args:
            plugin_name (str): The plugin name.

        Returns:
            None

        Raises:
            DockerPluginError: If the Kathara Network Plugin is not found on remote Docker connection.
            DockerPluginError: If the Kathara Network Plugin is not enabled on remote Docker connection.
        """
        try:
            logging.debug(f"Checking plugin `{plugin_name}`...")
            plugin = self.client.plugins.get(plugin_name)

            # Check for plugin updates.
            plugin.upgrade()
        except NotFound:
            if Setting.get_instance().remote_url is None:
                logging.info(f"Installing Kathara Network Plugin ({plugin_name})...")
                plugin = self.client.plugins.install(plugin_name)
                logging.info(f"Kathara Network Plugin ({plugin_name}) installed successfully!")
            else:
                raise DockerPluginError(
                    f"Kathara Network Plugin ({plugin_name}) not found on remote Docker connection."
                )

        if Setting.get_instance().remote_url is None:
            if plugin_name != f"{LINUX_PLUGIN_NAME}:{utils.get_architecture()}":
                if not plugin.enabled:
                    logging.debug(f"Enabling plugin `{plugin_name}`...")
                    plugin.enable()
            else:
                xtables_lock_mount = self._xtables_lock_mount()
                if not plugin.enabled:
                    self._configure_xtables_mount(plugin, xtables_lock_mount)
                    logging.debug(f"Enabling plugin `{plugin_name}`...")
                    plugin.enable()
                else:
                    # Get the mount of xtables.lock from the current plugin configuration
                    mount_obj = list(
                        filter(
                            lambda x: x["Name"] == XTABLES_CONFIGURATION_KEY,
                            plugin.attrs["Settings"]["Mounts"]
                        )
                    ).pop()

                    # If it's not equal to the computed one, fix the mount
                    if mount_obj["Source"] != xtables_lock_mount:
                        plugin.disable()
                        self._configure_xtables_mount(plugin, xtables_lock_mount)
                        logging.debug(f"Enabling plugin `{plugin_name}`...")
                        plugin.enable()
        else:
            if not plugin.enabled:
                raise DockerPluginError(
                    f"Kathara Network Plugin ({plugin_name}) not enabled on remote Docker connection."
                )

    def get_plugin_from_link_type(self, link_type: Optional[CollisionDomainTypesOption]) -> str:
        """Get plugin name from the link type.

        Args:
            link_type (Optional[str]): The link type. If None, defaults to the plugin in the settings.

        Returns:
            str: The Docker plugin name.
        """
        if link_type is None:
            return self._default_name

        return f"{LINK_TYPE_TO_PLUGIN[link_type]}:{utils.get_architecture()}"

    def exec_by_version(self, plugin_name: str, fun_vde: Callable, fun_bridge: Callable, fun_p2p: Callable) -> Any:
        """Executes the callback depending on the enabled plugin version.

        Returns:
            Any: The result of the callback.
        """
        # Strip architecture tag
        base_name = plugin_name.rsplit(":", 1)[0]

        if base_name == VDE_PLUGIN_NAME:
            return fun_vde(plugin_name)
        elif base_name == P2P_PLUGIN_NAME:
            return fun_p2p(plugin_name)
        elif base_name == LINUX_PLUGIN_NAME:
            return fun_bridge(plugin_name)
        else:
            raise DockerPluginError(f"Invalid plugin name `{plugin_name}`.")

    def plugin_pid(self, plugin_name: str) -> int:
        """Get the plugin process PID from the plugin state file.

        Args:
            plugin_name (str): The plugin name.

        Returns:
            int: The plugin process PID.
        """
        state = self._get_plugin_state(plugin_name)
        return state['init_process_pid']

    def plugin_store_path(self, plugin_name: str) -> str:
        """Get the plugin storage path (VDE only) from the plugin settings.

        Args:
            plugin_name (str): The plugin name.

        Returns:
            str: The plugin storage path.

        Raises:
            FileNotFoundError: If the storage path mount point cannot be found.
        """
        plugin = self.client.plugins.get(plugin_name)
        settings = plugin.settings

        hosttmp_mount = None
        for mount in settings['Mounts']:
            if mount['Name'] == HOSTTMP_KEY:
                hosttmp_mount = mount['Destination']
                break

        if hosttmp_mount:
            return os.path.join(hosttmp_mount, "katharanp")

        raise FileNotFoundError(f"Unable to find `{HOSTTMP_KEY}` in plugin mounts.")

    def _get_plugin_state(self, plugin_name: str) -> Dict:
        """Get the plugin state.json file content from the Docker plugin state path.

        Args:
            plugin_name (str): The plugin name.

        Returns:
            Dict: The content of the state.json file, parsed. Empty dict if the file cannot be found.
        """
        plugin = self.client.plugins.get(plugin_name)
        plugin_state_json = self.PLUGIN_STATE_PATH.format(id=plugin.id)
        if not os.path.exists(plugin_state_json):
            return {}
        with open(plugin_state_json, "r") as state_file:
            return json.loads(state_file.read())

    def _xtables_lock_mount(self) -> str:
        """Get the xtables.lock path depending on the host iptables version (Linux bridge only).

        Returns:
            str: The xtables.lock path.
        """

        def _mount_xtables_lock_linux():
            iptables_version = Networking.get_iptables_version()
            return "" if 'nf_tables' in iptables_version else XTABLES_LOCK_PATH

        def _mount_xtables_lock_windows():
            docker_info = self.client.info()
            return "" if 'microsoft' not in docker_info['KernelVersion'] else XTABLES_LOCK_PATH

        return utils.exec_by_platform(_mount_xtables_lock_linux, _mount_xtables_lock_windows, lambda: "")

    @staticmethod
    def _configure_xtables_mount(plugin: Plugin, xtables_lock_mount: str) -> None:
        """Changes the Docker plugin configuration by settings the correct xtables.lock path (Linux bridge only).

        Args:
            plugin (Plugin): The plugin to configure.
            xtables_lock_mount (str): The xtables.lock path.

        Returns:
            None
        """
        logging.debug(f"Configuring xtables.lock source to `{xtables_lock_mount}`...")
        plugin.configure({
            XTABLES_CONFIGURATION_KEY + '.source': xtables_lock_mount
        })
