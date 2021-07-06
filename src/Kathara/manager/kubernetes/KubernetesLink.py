import hashlib
import logging
import re
from functools import partial
from multiprocessing import Manager
from multiprocessing.dummy import Pool

import progressbar
from kubernetes import client
from kubernetes.client.api import custom_objects_api
from kubernetes.client.rest import ApiException

from .KubernetesConfig import KubernetesConfig
from ... import utils
from ...setting.Setting import Setting

MAX_K8S_LINK_NUMBER = (1 << 24) - 10

K8S_NET_GROUP = "k8s.cni.cncf.io"
K8S_NET_VERSION = "v1"
K8S_NET_PLURAL = "network-attachment-definitions"


class KubernetesLink(object):
    __slots__ = ['client', 'seed']

    def __init__(self):
        self.client = custom_objects_api.CustomObjectsApi()

        self.seed = KubernetesConfig.get_cluster_user()

    def deploy_links(self, lab):
        links = lab.links.items()

        if len(links) > 0:
            pool_size = utils.get_pool_size()
            link_pool = Pool(pool_size)

            items = utils.chunk_list(links, pool_size)

            progress_bar = None
            if utils.CLI_ENV:
                progress_bar = progressbar.ProgressBar(
                    widgets=['Deploying collision domains... ', progressbar.Bar(),
                             ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
                    redirect_stdout=True,
                    max_value=len(links)
                )

            with Manager() as manager:
                network_ids = manager.dict()

                for chunk in items:
                    link_pool.map(func=partial(self._deploy_link, progress_bar, network_ids), iterable=chunk)

            if utils.CLI_ENV:
                progress_bar.finish()

    def _deploy_link(self, progress_bar, network_ids, link_item):
        (_, link) = link_item

        network_id = self._get_unique_network_id(link.name, network_ids)
        self.create(link, network_id)

        if progress_bar is not None:
            progress_bar += 1

    def create(self, link, network_id):
        # If a network with the same name exists, return it instead of creating a new one.
        network_objects = self.get_links_by_filters(lab_hash=link.lab.hash, link_name=link.name)
        if network_objects:
            link.api_object = network_objects.pop()
            return

        link.api_object = self.client.create_namespaced_custom_object(group=K8S_NET_GROUP,
                                                                      version=K8S_NET_VERSION,
                                                                      namespace=link.lab.hash,
                                                                      plural=K8S_NET_PLURAL,
                                                                      body=self._build_definition(link, network_id)
                                                                      )

        # If external is defined for a link, throw a warning.
        if link.external:
            logging.warning('External is not supported on Megalos. It will be ignored.')

    def undeploy(self, lab_hash, networks_to_delete=None):
        links = self.get_links_by_filters(lab_hash=lab_hash)
        if networks_to_delete is not None and len(networks_to_delete) > 0:
            links = [item for item in links if item["metadata"]["name"] in networks_to_delete]

        if len(links) > 0:
            pool_size = utils.get_pool_size()
            links_pool = Pool(pool_size)

            items = utils.chunk_list(links, pool_size)

            progress_bar = None
            if utils.CLI_ENV:
                progress_bar = progressbar.ProgressBar(
                    widgets=['Deleting collision domains... ', progressbar.Bar(),
                             ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
                    redirect_stdout=True,
                    max_value=len(links)
                )

            for chunk in items:
                links_pool.map(func=partial(self._undeploy_link, progress_bar), iterable=chunk)

            if utils.CLI_ENV:
                progress_bar.finish()

    def wipe(self):
        links = self.get_links_by_filters()

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, None), iterable=chunk)

    def _undeploy_link(self, progress_bar, link_item):
        namespace = link_item["metadata"]["namespace"]

        try:
            self.client.delete_namespaced_custom_object(group=K8S_NET_GROUP,
                                                        version=K8S_NET_VERSION,
                                                        namespace=namespace,
                                                        plural=K8S_NET_PLURAL,
                                                        name=link_item["metadata"]["name"],
                                                        body=client.V1DeleteOptions(grace_period_seconds=0),
                                                        grace_period_seconds=0
                                                        )
        except ApiException:
            pass

        if progress_bar is not None:
            progress_bar += 1

    def get_links_by_filters(self, lab_hash=None, link_name=None):
        filters = ["app=kathara"]
        if link_name:
            filters.append("name=%s" % link_name)

        return self.client.list_namespaced_custom_object(group=K8S_NET_GROUP,
                                                         version=K8S_NET_VERSION,
                                                         namespace=lab_hash if lab_hash else "default",
                                                         plural=K8S_NET_PLURAL,
                                                         label_selector=",".join(filters),
                                                         timeout_seconds=9999
                                                         )["items"]

    def _build_definition(self, link, network_id):
        return {
            "apiVersion": "k8s.cni.cncf.io/v1",
            "kind": "NetworkAttachmentDefinition",
            "metadata": {
                "name": self.get_network_name(link.name),
                "labels": {
                    "name": link.name,
                    "app": "kathara"
                }
            },
            "spec": {
                "config": """{
                            "cniVersion": "0.3.0",
                            "name": "%s",
                            "type": "megalos",
                            "suffix": "%s",
                            "vxlanId": %d
                        }""" % (link.name.lower(), link.lab.hash[0:6], network_id)
            }
        }

    def _get_unique_network_id(self, name, network_ids):
        network_id = self._get_network_id(name)
        offset = 1
        while network_id in network_ids:
            network_id = self._get_network_id(name, offset)
            offset += 1

        network_ids[network_id] = 1

        return network_id

    def _get_network_id(self, name, offset=0):
        network_name = self.seed + name
        return (offset + int(hashlib.sha256(network_name.encode('utf-8')).hexdigest(), 16)) % MAX_K8S_LINK_NUMBER

    @staticmethod
    def get_network_name(name):
        suffix = ''
        # Underscore is replaced with -, but to keep name uniqueness append 8 chars of hash from the original name
        if '_' in name:
            suffix = '-%s' % hashlib.md5(name.encode('utf-8', errors='ignore')).hexdigest()[:8]
            name = name.replace('_', '-')

        link_name = "%s-%s%s" % (Setting.get_instance().net_prefix, name, suffix)
        return re.sub(r'[^0-9a-z\-.]+', '', link_name.lower())
