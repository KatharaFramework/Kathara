import logging
from typing import Callable

from docker import DockerClient
from docker.errors import NotFound

from ... import utils
from ...os.Networking import Networking
from ...setting.Setting import Setting

PLUGIN_NAME = "kathara/katharanp:" + utils.get_architecture()
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
        """

        try:
            logging.debug("Checking plugin `%s`..." % PLUGIN_NAME)
            plugin = self.client.plugins.get(PLUGIN_NAME)
            # Check for plugin updates.
            plugin.upgrade()
        except NotFound:
            if Setting.get_instance().remote_url is None:
                logging.info("Installing Kathara Network Plugin...")
                plugin = self.client.plugins.install(PLUGIN_NAME)
                logging.info("Kathara Network Plugin installed successfully!")
            else:
                raise Exception("Kathara Network Plugin not found on remote Docker connection.")

        if Setting.get_instance().remote_url is None:
            xtables_lock_mount = self._get_xtables_lock_mount()
            if not plugin.enabled:
                self._configure_xtables_mount(plugin, xtables_lock_mount)
                logging.debug("Enabling plugin `%s`..." % PLUGIN_NAME)
                plugin.enable()
            else:
                # Get the mount of xtables.lock from the current plugin configuration
                mount_obj = list(filter(lambda x: x["Name"] == XTABLES_CONFIGURATION_KEY,
                                        plugin.attrs["Settings"]["Mounts"])).pop()

                # If it's not equal to the computed one, fix the mount
                if mount_obj["Source"] != xtables_lock_mount:
                    plugin.disable()
                    self._configure_xtables_mount(plugin, xtables_lock_mount)
                    logging.debug("Enabling plugin `%s`..." % PLUGIN_NAME)
                    plugin.enable()
        else:
            if not plugin.enabled:
                raise Exception("Kathara Network Plugin not enabled on remote Docker connection.")

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
