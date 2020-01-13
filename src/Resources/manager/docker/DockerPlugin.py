from docker.errors import NotFound
import logging

PLUGIN_NAME = "kathara/katharanp:latest"


class DockerPlugin(object):
    __slots__ = ['client']

    def __init__(self, client):
        self.client = client

    def check_and_download_plugin(self):
        try:
            logging.debug("Checking plugin `%s`..." % PLUGIN_NAME)

            plugin = self.client.plugins.get(PLUGIN_NAME)

        except NotFound:
            logging.info("Installing Kathara Network Plugin...")
            plugin = self.client.plugins.install(PLUGIN_NAME)
            logging.info("Kathara Network Plugin installed successfully!")

        if not plugin.enabled:
            logging.debug("Enabling plugin `%s`..." % PLUGIN_NAME)
            plugin.enable()
