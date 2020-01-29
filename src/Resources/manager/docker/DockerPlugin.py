import logging

from docker.errors import NotFound

from ... import utils
from ...os.Networking import Networking

PLUGIN_NAME = "kathara/katharanp"
BUSTER_TAG = "buster"
STRETCH_TAG = "stretch"


class DockerPlugin(object):
    __slots__ = ['client', 'plugin_name']

    def __init__(self, client):
        self.client = client

        def _select_plugin_name_linux():
            iptables_version = Networking.get_iptables_version()

            return "%s:%s" % (PLUGIN_NAME, BUSTER_TAG) if 'nf_tables' in iptables_version else \
                   "%s:%s" % (PLUGIN_NAME, STRETCH_TAG)

        self.plugin_name = utils.exec_by_platform(_select_plugin_name_linux,
                                                  lambda: "%s:%s" % (PLUGIN_NAME, BUSTER_TAG),
                                                  lambda: "%s:%s" % (PLUGIN_NAME, BUSTER_TAG)
                                                  )

    def check_and_download_plugin(self):
        try:
            logging.debug("Checking plugin `%s`..." % self.plugin_name)

            plugin = self.client.plugins.get(self.plugin_name)
            # Check for plugin updates.
            plugin.upgrade()
        except NotFound:
            logging.info("Installing Kathara Network Plugin...")
            plugin = self.client.plugins.install(self.plugin_name)
            logging.info("Kathara Network Plugin installed successfully!")

        if not plugin.enabled:
            logging.debug("Enabling plugin `%s`..." % self.plugin_name)
            plugin.enable()
