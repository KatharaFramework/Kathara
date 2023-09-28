import json
import logging
import os.path
from typing import Callable, Any, Dict

from docker import DockerClient
from docker.errors import NotFound

from ... import utils
from ...exceptions import DockerPluginError
from ...os.Networking import Networking
from ...setting.Setting import Setting

LINUX_PLUGIN_NAME = "kathara/katharanp"
VDE_PLUGIN_NAME = "kathara/katharanp_vde"

HOSTTMP_KEY = "tmp"
XTABLES_CONFIGURATION_KEY = "xtables_lock"
XTABLES_LOCK_PATH = "/run/xtables.lock"


class DockerPlugin(object):
    """Class responsible for interacting with Docker Plugins."""
    __slots__ = ['client', 'current_name']

    PLUGIN_STATE_PATH = "/run/docker/runtime-runc/plugins.moby/{id}/state.json"

    def __init__(self, client: DockerClient):
        self.client: DockerClient = client
        self.current_name: str = f"{Setting.get_instance().network_plugin}:{utils.get_architecture()}"

    def check_and_download_plugin(self) -> None:
        """Check the presence of the Kathara Network Plugin and download it or upgrade it, if needed.

        Returns:
            None

        Raises:
            DockerPluginError: If the Kathara Network Plugin is not found on remote Docker connection.
            DockerPluginError: If the Kathara Network Plugin is not enabled on remote Docker connection.
        """
        try:
            logging.debug("Checking plugin `%s`..." % self.current_name)
            plugin = self.client.plugins.get(self.current_name)

            # Check for plugin updates.
            plugin.upgrade()
        except NotFound:
            if Setting.get_instance().remote_url is None:
                logging.info(f"Installing Kathara Network Plugin ({self.current_name})...")
                plugin = self.client.plugins.install(self.current_name)
                logging.info("Kathara Network Plugin installed successfully!")
            else:
                raise DockerPluginError("Kathara Network Plugin not found on remote Docker connection.")

        if Setting.get_instance().remote_url is None:
            if self.is_vde() and not plugin.enabled:
                logging.debug("Enabling plugin `%s`..." % self.current_name)
                plugin.enable()
            elif self.is_bridge():
                xtables_lock_mount = self._xtables_lock_mount()
                if not plugin.enabled:
                    self._configure_xtables_mount(plugin, xtables_lock_mount)
                    logging.debug("Enabling plugin `%s`..." % self.current_name)
                    plugin.enable()
                else:
                    # Get the mount of xtables.lock from the current plugin configuration
                    mount_obj = list(filter(lambda x: x["Name"] == XTABLES_CONFIGURATION_KEY,
                                            plugin.attrs["Settings"]["Mounts"])).pop()

                    # If it's not equal to the computed one, fix the mount
                    if mount_obj["Source"] != xtables_lock_mount:
                        plugin.disable()
                        self._configure_xtables_mount(plugin, xtables_lock_mount)
                        logging.debug("Enabling plugin `%s`..." % self.current_name)
                        plugin.enable()
        else:
            if not plugin.enabled:
                raise DockerPluginError("Kathara Network Plugin not enabled on remote Docker connection.")

    @staticmethod
    def is_vde() -> bool:
        """Check if the current enabled plugin is the VDE version.

        Returns:
            bool: True if the running plugin is the VDE version.
        """
        return Setting.get_instance().network_plugin == VDE_PLUGIN_NAME

    @staticmethod
    def is_bridge() -> bool:
        """Check if the current enabled plugin is the Linux bridge version.

        Returns:
            bool: True if the running plugin is the Linux bridge version.
        """
        return Setting.get_instance().network_plugin == LINUX_PLUGIN_NAME

    def exec_by_version(self, fun_vde: Callable, fun_bridge: Callable) -> Any:
        """Executes the callback depending on the enabled plugin version.

        Returns:
            Any: The result of the callback.
        """
        if self.is_vde():
            return fun_vde()
        elif self.is_bridge():
            return fun_bridge()

    def plugin_pid(self) -> int:
        """Get the plugin process PID from the plugin state file.

        Returns:
            int: The plugin process PID.
        """
        state = self._get_plugin_state()
        return state['init_process_pid']

    def plugin_store_path(self) -> str:
        """Get the plugin storage path (VDE only) from the plugin settings.

        Returns:
            str: The plugin storage path.

        Raises:
            FileNotFoundError: If the storage path mount point cannot be found.
        """
        plugin = self.client.plugins.get(self.current_name)
        settings = plugin.settings

        hosttmp_mount = None
        for mount in settings['Mounts']:
            if mount['Name'] == HOSTTMP_KEY:
                hosttmp_mount = mount['Destination']
                break

        if hosttmp_mount:
            return os.path.join(hosttmp_mount, "katharanp")

        raise FileNotFoundError(f"Unable to find `{HOSTTMP_KEY}` in plugin mounts.")

    def _get_plugin_state(self) -> Dict:
        """Get the plugin state.json file content from the Docker plugin state path.

        Returns:
            Dict: The content of the state.json file, parsed. Empty dict if the file cannot be found.
        """
        plugin = self.client.plugins.get(self.current_name)
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
    def _configure_xtables_mount(plugin, xtables_lock_mount) -> None:
        """Changes the Docker plugin configuration by settings the correct xtables.lock path (Linux bridge only).

        Returns:
            None
        """
        logging.debug("Configuring xtables.lock source to `%s`..." % xtables_lock_mount)
        plugin.configure({
            XTABLES_CONFIGURATION_KEY + '.source': xtables_lock_mount
        })
