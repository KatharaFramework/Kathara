import docker
import os

from classes.setting.Setting import Setting


class DockerLinkDeployer(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = docker.from_env()

    def deploy(self, link):
        link.network_object = self.client.networks.create(name=self._get_network_name(link.name),
                                                          driver='bridge',
                                                          check_duplicate=True,
                                                          labels={"lab_hash": link.lab.folder_hash,
                                                                  "app": "kathara"
                                                                  }
                                                          )

    def undeploy(self, lab_hash):
        self.client.networks.prune(filters={"label": "lab_hash=%s" % lab_hash})

    def wipe(self):
        self.client.networks.prune(filters={"label": "app=kathara"})

    # noinspection PyMethodMayBeStatic
    def _get_network_name(self, name):
        return "%s_%s_%s" % (Setting.get_instance().net_prefix, os.getlogin(), name)
