import logging

from docker.errors import NotFound

PLUGIN_NAME = "kathara/katharanp:latest"


class DockerPlugin(object):
    __slots__ = ['client']

    def check_and_download_plugin(self):
        try:
            logging.debug("Checking plugin `%s`..." % PLUGIN_NAME)

            plugin = self.client.plugins.get(PLUGIN_NAME)
            # Check for plugin updates.
            plugin.upgrade()
        except NotFound:
            logging.info("Installing Kathara Network Plugin...")
            plugin = self.client.plugins.install(PLUGIN_NAME)
            logging.info("Kathara Network Plugin installed successfully!")

        if not plugin.enabled:
            logging.debug("Enabling plugin `%s`..." % PLUGIN_NAME)
            plugin.enable()
