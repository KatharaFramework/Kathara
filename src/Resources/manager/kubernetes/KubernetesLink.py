import hashlib
import logging
import re
from functools import partial
from multiprocessing.dummy import Pool

from kubernetes import client
from kubernetes.client.apis import custom_objects_api
from kubernetes.client.rest import ApiException
from progress.bar import Bar

from .KubernetesConfig import KubernetesConfig
from ... import utils
from ...setting.Setting import Setting

MAX_K8S_LINK_NUMBER = (1 << 24) - 20

K8S_NET_GROUP = "k8s.cni.cncf.io"
K8S_NET_VERSION = "v1"
K8S_NET_PLURAL = "network-attachment-definitions"


class KubernetesLink(object):
    __slots__ = ['client', 'seed']

    def __init__(self):
        self.client = custom_objects_api.CustomObjectsApi()

        self._get_link_number_seed()

    def deploy_links(self, lab):
        pool_size = utils.get_pool_size()
        link_pool = Pool(pool_size)

        links = lab.links.items()
        items = utils.chunk_list(links, pool_size)

        progress_bar = Bar('Deploying links...', max=len(links))

        for chunk in items:
            link_pool.map(func=partial(self._deploy_link, progress_bar), iterable=chunk)

        progress_bar.finish()

    def _deploy_link(self, progress_bar, link_item):
        (_, link) = link_item

        self.create(link)

        progress_bar.next()

    def create(self, link):
        if '_' in link.name:
            logging.warning("Link name `%s` not valid for Kubernetes API Server, changed to `%s`." %
                            (link.name, link.name.replace('_', '-')))

        # If a network with the same name exists, return it instead of creating a new one.
        network_objects = self.get_links_by_filters(lab_hash=link.lab.folder_hash, link_name=link.name)
        if network_objects:
            link.api_object = network_objects.pop()
            return

        link.api_object = self.client.create_namespaced_custom_object(group=K8S_NET_GROUP,
                                                                      version=K8S_NET_VERSION,
                                                                      namespace=link.lab.folder_hash,
                                                                      plural=K8S_NET_PLURAL,
                                                                      body=self._build_definition(link)
                                                                      )

    def undeploy(self, lab_hash, networks_to_delete=None):
        links = self.get_links_by_filters(lab_hash=lab_hash)

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        progress_bar = Bar("Deleting links...", max=len(links) if not networks_to_delete
                                                               else len(networks_to_delete)
                           )

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, networks_to_delete, True, progress_bar), iterable=chunk)

        progress_bar.finish()

    def wipe(self):
        links = self.get_links_by_filters()

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, [], False, None), iterable=chunk)

    def _undeploy_link(self, networks_to_delete, log, progress_bar, link_item):
        namespace = link_item["metadata"]["namespace"]

        if networks_to_delete is not None and link_item["metadata"]["name"] not in networks_to_delete:
            return

        try:
            self.client.delete_namespaced_custom_object(group=K8S_NET_GROUP,
                                                        version=K8S_NET_VERSION,
                                                        namespace=namespace,
                                                        plural=K8S_NET_PLURAL,
                                                        name=link_item["metadata"]["name"],
                                                        body=client.V1DeleteOptions(grace_period_seconds=0),
                                                        grace_period_seconds=0
                                                        )

            if log:
                progress_bar.next()
        except ApiException:
            return

    def get_links_by_filters(self, lab_hash=None, link_name=None):
        filters = ["app=kathara"]
        if link_name:
            filters.append("name=%s" % link_name)

        return self.client.list_namespaced_custom_object(group=K8S_NET_GROUP,
                                                         version=K8S_NET_VERSION,
                                                         namespace=lab_hash if lab_hash else "default",
                                                         plural=K8S_NET_PLURAL,
                                                         label_selector=",".join(filters)
                                                         )["items"]

    def _build_definition(self, link):
        network_id = self._get_link_identifier(link.name)

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
                        }""" % (link.name.lower(), link.lab.folder_hash[0:6], network_id)
            }
        }

    def _get_link_number_seed(self):
        cluster_user = KubernetesConfig.get_cluster_user()
        self.seed = int(hashlib.sha1(cluster_user.encode('utf-8')).hexdigest(), 16)

    def _get_link_identifier(self, name):
        name_seed = int(hashlib.sha1(name.encode('utf-8')).hexdigest(), 16)
        name_seed = (self.seed + name_seed) % MAX_K8S_LINK_NUMBER
        return 10 + name_seed

    @staticmethod
    def get_network_name(name):
        suffix = ''
        # Underscore is replaced with -, but to keep name uniqueness append 8 chars of hash from the original name
        if '_' in name:
            suffix = '-%s' % hashlib.md5(name.encode('utf-8', errors='ignore')).hexdigest()[:8]
            name = name.replace('_', '-')

        link_name = "%s-%s%s" % (Setting.get_instance().net_prefix, name, suffix)
        return re.sub(r'[^0-9a-z\-.]+', '', link_name.lower())
