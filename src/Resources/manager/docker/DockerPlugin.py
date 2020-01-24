from docker.errors import NotFound
import logging
import os
from ... import utils

PLUGIN_NAME = "kathara/katharanp"
PLUGIN_NAME_BUSTER = "kathara/katharanp:buster"
PLUGIN_NAME_STRETCH = "kathara/katharanp:stretch"

class DockerPlugin(object):
    __slots__ = ['client', 'plugin_name']

    def __init__(self, client):
        self.client = client
        self.plugin_name = ""
        utils.exec_by_platform(self._select_plugin_name_linux, self._select_plugin_name, self._select_plugin_name)

    def _select_plugin_name_linux(self):
        iptables_version = os.popen("iptables --version").read().strip()
        
        if 'nf_tables' in iptables_version:
            self.plugin_name = PLUGIN_NAME_BUSTER
        else: 
            self.plugin_name = PLUGIN_NAME_STRETCH

    def _select_plugin_name(self): 
        self.plugin_name = PLUGIN_NAME_BUSTER

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
