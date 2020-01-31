import re
from functools import partial
from multiprocessing.dummy import Pool

from kubernetes import client
from kubernetes.client.apis import custom_objects_api
from progress.bar import Bar

from ... import utils
from ...setting.Setting import Setting

K8S_NET_GROUP = "k8s.cni.cncf.io"
K8S_NET_VERSION = "v1"
K8S_NET_PLURAL = "network-attachment-definitions"


class KubernetesLink(object):
    __slots__ = ['client']

    def __init__(self):
        self.client = custom_objects_api.CustomObjectsApi()

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
        # If a network with the same name exists, return it instead of creating a new one.
        link_name = self.get_network_name(link.name)

        network_objects = self.get_links_by_filters(lab_hash=link.lab.folder_hash, link_name=link_name)
        if network_objects:
            link.api_object = network_objects.pop()
            return

        link.api_object = self.client.create_namespaced_custom_object(group=K8S_NET_GROUP,
                                                                      version=K8S_NET_VERSION,
                                                                      namespace=link.lab.folder_hash,
                                                                      plural=K8S_NET_PLURAL,
                                                                      body=self._build_definition(link)
                                                                      )

    def undeploy(self, lab_hash):
        links = self.get_links_by_filters(lab_hash=lab_hash)

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        progress_bar = Bar("Deleting links...", max=len(links))

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, True, progress_bar), iterable=chunk)

        progress_bar.finish()

    def wipe(self):
        links = self.get_links_by_filters()

        pool_size = utils.get_pool_size()
        links_pool = Pool(pool_size)

        items = utils.chunk_list(links, pool_size)

        for chunk in items:
            links_pool.map(func=partial(self._undeploy_link, False, None), iterable=chunk)

    def _undeploy_link(self, log, progress_bar, link_item):
        self.client.delete_namespaced_custom_object(group=K8S_NET_GROUP,
                                                    version=K8S_NET_VERSION,
                                                    namespace=link_item["metadata"]["namespace"],
                                                    plural=K8S_NET_PLURAL,
                                                    name=self.get_network_name(link_item["metadata"]["name"]),
                                                    body=client.V1DeleteOptions(grace_period_seconds=0),
                                                    grace_period_seconds=0
                                                    )

        if log:
            progress_bar.next()

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
        # TODO: FIND A WAY TO HANDLE VLAN_ID
        vlan_id = 0
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
                            "type": "megalos",
                            "suffix": "%s",
                            "vlanId": %d
                        }""" % (link.lab.folder_hash[0:6], 10 + vlan_id)
            }
        }

    @staticmethod
    def get_network_name(name):
        link_name = "%s-%s" % (Setting.get_instance().net_prefix, name)
        return re.sub(r'[^0-9a-z\-.]+', '', link_name.lower())
