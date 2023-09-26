import logging
from typing import Callable

from docker import DockerClient
from docker.errors import NotFound

from ... import utils
from ...exceptions import DockerPluginError
from ...os.Networking import Networking
from ...setting.Setting import Setting

BRIDGE_PLUGIN_NAME = "kathara/katharanp"
VDE_PLUGIN_NAME = "kathara/katharanp_vde"
XTABLES_CONFIGURATION_KEY = "xtables_lock"
XTABLES_LOCK_PATH = "/run/xtables.lock"


class DockerPlugin(object):
    """Class responsible for interacting with Docker Plugins."""
    __slots__ = ['client']

    def __init__(self, client: DockerClient):
        self.client: DockerClient = client

    def check_and_download_plugin(self) -> None:
        """Check the presence of the Kathara Network Plugin and download it or upgrade it, if needed.

        Returns:
            None

        Raises:
            DockerPluginError: If the Kathara Network Plugin is not found on remote Docker connection.
            DockerPluginError: If the Kathara Network Plugin is not enabled on remote Docker connection.
        """
        settings = Setting.get_instance()
        network_plugin = f"{settings.network_plugin}:{utils.get_architecture()}"
        try:
            logging.debug("Checking plugin `%s`..." % network_plugin)
            plugin = self.client.plugins.get(network_plugin)

            # Check for plugin updates.
            plugin.upgrade()

        except NotFound:
            if settings.remote_url is None:
                logging.info(f"Installing Kathara Network Plugin ({network_plugin})...")
                plugin = self.client.plugins.install(network_plugin)
                logging.info("Kathara Network Plugin installed successfully!")
            else:
                raise DockerPluginError("Kathara Network Plugin not found on remote Docker connection.")

        if settings.network_plugin == VDE_PLUGIN_NAME and settings.remote_url is None and not plugin.enabled:
            plugin.enable()
        elif settings.network_plugin == BRIDGE_PLUGIN_NAME and settings.remote_url is None:
            xtables_lock_mount = self._get_xtables_lock_mount()
            if not plugin.enabled:
                self._configure_xtables_mount(plugin, xtables_lock_mount)
                logging.debug("Enabling plugin `%s`..." % network_plugin)
                plugin.enable()
            else:
                # Get the mount of xtables.lock from the current plugin configuration
                mount_obj = list(filter(lambda x: x["Name"] == XTABLES_CONFIGURATION_KEY,
                                        plugin.attrs["Settings"]["Mounts"])).pop()

                # If it's not equal to the computed one, fix the mount
                if mount_obj["Source"] != xtables_lock_mount:
                    plugin.disable()
                    self._configure_xtables_mount(plugin, xtables_lock_mount)
                    logging.debug("Enabling plugin `%s`..." % network_plugin)
                    plugin.enable()
        else:
            if not plugin.enabled:
                raise DockerPluginError("Kathara Network Plugin not enabled on remote Docker connection.")

    def _get_xtables_lock_mount(self) -> Callable:
        def _mount_xtables_lock_linux():
            iptables_version = Networking.get_iptables_version()
            return "" if 'nf_tables' in iptables_version else XTABLES_LOCK_PATH

        def _mount_xtables_lock_windows():
            docker_info = self.client.info()
            return "" if 'microsoft' not in docker_info['KernelVersion'] else XTABLES_LOCK_PATH

        return utils.exec_by_platform(_mount_xtables_lock_linux, _mount_xtables_lock_windows, lambda: "")

    @staticmethod
    def _configure_xtables_mount(plugin, xtables_lock_mount) -> None:
        logging.debug("Configuring xtables.lock source to `%s`..." % xtables_lock_mount)
        plugin.configure({
            XTABLES_CONFIGURATION_KEY + '.source': xtables_lock_mount
        })
