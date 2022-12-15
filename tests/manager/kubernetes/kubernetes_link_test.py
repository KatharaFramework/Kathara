import copy
import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from kubernetes import client

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.manager.kubernetes.KubernetesLink import KubernetesLink
from src.Kathara.exceptions import LinkNotFoundError


class FakeConfig(object):
    def __init__(self):
        self.api_key = {
            'authorization': 'user123'
        }


class FakeManager(object):
    def __init__(self, ctx):
        pass

    def start(self):
        pass

    def __enter__(self):
        return self

    def dict(self, init_dict):
        return init_dict

    def __exit__(self, exit_type, value, traceback):
        return True


EXPECTED_NETWORK_ID = 4694369
NETWORK_IDS_SINGLE = {
    4694369: 1
}
NETWORK_IDS_DOUBLE = {
    4694369: 1,
    4694370: 1
}


#
# FIXTURE
#
@pytest.fixture()
def default_link():
    from src.Kathara.model.Link import Link
    return Link(Lab("default_scenario"), "A")


@pytest.fixture()
@mock.patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi")
@mock.patch("kubernetes.client.Configuration")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_link(kubernetes_namespace_mock, config_mock, _):
    config_mock.get_default_copy.return_value = FakeConfig()

    return KubernetesLink(kubernetes_namespace_mock)


@pytest.fixture()
def kubernetes_network():
    return {
        "apiVersion": "k8s.cni.cncf.io/v1",
        "kind": "NetworkAttachmentDefinition",
        "metadata": {
            "name": "netprefix-a",
            "namespace": "FwFaxbiuhvSWb2KpN5zw",
            "labels": {
                "name": "A",
                "app": "kathara"
            }
        },
        "spec": {
            "config": """{
                            "cniVersion": "0.3.0",
                            "name": "a",
                            "type": "megalos",
                            "suffix": "FwFaxb",
                            "vxlanId": 1
                        }"""
        }
    }


#
# TEST: get_network_name
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_network_name(mock_setting_get_instance, kubernetes_link):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    link_name = kubernetes_link.get_network_name("a")
    assert link_name == "netprefix-a"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_network_name_with_underscore(mock_setting_get_instance, kubernetes_link):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    k8s_link_name = kubernetes_link.get_network_name("a_b")

    assert k8s_link_name == "netprefix-a-b-dbf08e00"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_network_name_remove_invalid_chars(mock_setting_get_instance, kubernetes_link):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    k8s_link_name = kubernetes_link.get_network_name("A05#")

    assert k8s_link_name == "netprefix-a05"


#
# TEST: _build_definition
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_build_definition(mock_setting_get_instance, default_link, kubernetes_link):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    expected_definition = {
        "apiVersion": "k8s.cni.cncf.io/v1",
        "kind": "NetworkAttachmentDefinition",
        "metadata": {
            "name": "netprefix-a",
            "labels": {
                "name": "A",
                "app": "kathara"
            }
        },
        "spec": {
            "config": """{
                            "cniVersion": "0.3.0",
                            "name": "a",
                            "type": "megalos",
                            "suffix": "FwFaxb",
                            "vxlanId": 1
                        }"""
        }
    }
    actual_definition = kubernetes_link._build_definition(default_link, 1)

    assert actual_definition == expected_definition


#
# TEST: _get_network_id
#
def test_get_network_id(kubernetes_link):
    actual_id = kubernetes_link._get_network_id("a", 0)

    assert actual_id == EXPECTED_NETWORK_ID


def test_get_network_id_offset(kubernetes_link):
    expected_id = EXPECTED_NETWORK_ID + 1
    actual_id = kubernetes_link._get_network_id("a", 1)

    assert actual_id == expected_id


#
# TEST: _get_unique_network_id
#
def test_get_unique_network_id(kubernetes_link):
    network_ids = {}

    actual_network_id = kubernetes_link._get_unique_network_id("a", network_ids)

    assert actual_network_id == EXPECTED_NETWORK_ID
    assert network_ids == {4694369: 1}


def test_get_unique_network_id_collision(kubernetes_link):
    expected_network_id = EXPECTED_NETWORK_ID + 1
    actual_network_id = kubernetes_link._get_unique_network_id("a", NETWORK_IDS_SINGLE)

    assert actual_network_id == expected_network_id
    assert NETWORK_IDS_SINGLE == {4694369: 1, expected_network_id: 1}


def test_get_unique_network_id_double_collision(kubernetes_link):
    expected_network_id = EXPECTED_NETWORK_ID + 2
    actual_network_id = kubernetes_link._get_unique_network_id("a", NETWORK_IDS_DOUBLE)

    assert actual_network_id == expected_network_id
    assert NETWORK_IDS_DOUBLE == {4694369: 1, 4694370: 1, expected_network_id: 1}


#
# TEST: create
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_create(mock_setting_get_instance, kubernetes_link, default_link):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    kubernetes_link.client.list_namespaced_custom_object.return_value = {
        "items": []
    }

    network_definition = {
        "apiVersion": "k8s.cni.cncf.io/v1",
        "kind": "NetworkAttachmentDefinition",
        "metadata": {
            "name": "netprefix-a",
            "labels": {
                "name": "A",
                "app": "kathara"
            }
        },
        "spec": {
            "config": """{
                            "cniVersion": "0.3.0",
                            "name": "a",
                            "type": "megalos",
                            "suffix": "FwFaxb",
                            "vxlanId": 1
                        }"""
        }
    }

    kubernetes_link.create(default_link, 1)
    kubernetes_link.client.create_namespaced_custom_object.assert_called_once_with(
        group="k8s.cni.cncf.io",
        version="v1",
        namespace=default_link.lab.hash,
        plural="network-attachment-definitions",
        body=network_definition
    )


#
# TEST: _deploy_link
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.create")
def test_deploy_link(mock_create, kubernetes_link, default_link):
    kubernetes_link._deploy_link({}, ("", default_link))
    mock_create.called_once_with(default_link, EXPECTED_NETWORK_ID)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.create")
def test_deploy_link_collision(mock_create, kubernetes_link, default_link):
    kubernetes_link._deploy_link(NETWORK_IDS_SINGLE, ("", default_link))
    mock_create.called_once_with(default_link, EXPECTED_NETWORK_ID + 1)


#
# TEST: deploy_links
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink._deploy_link")
@mock.patch("multiprocessing.managers.SyncManager", new=FakeManager)
def test_deploy_links(mock_deploy_link, mock_get_links_by_filters, kubernetes_link):
    mock_get_links_by_filters.return_value = []

    lab = Lab("Default scenario")
    link_a = lab.get_or_new_link("A")
    link_b = lab.get_or_new_link("B")
    link_c = lab.get_or_new_link("C")

    kubernetes_link.deploy_links(lab)

    mock_deploy_link.assert_any_call({}, ("A", link_a))
    mock_deploy_link.assert_any_call({}, ("B", link_b))
    mock_deploy_link.assert_any_call({}, ("C", link_c))
    assert mock_deploy_link.call_count == 3


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink._deploy_link")
def test_deploy_links_no_link(mock_deploy_link, kubernetes_link):
    lab = Lab("Default scenario")

    kubernetes_link.deploy_links(lab)

    assert not mock_deploy_link.called


#
# TEST: _undeploy_link
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_delete_link(mock_setting_get_instance, kubernetes_network, kubernetes_link, default_link):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    kubernetes_link.client.list_namespaced_custom_object.return_value = {
        "items": []
    }

    kubernetes_link._undeploy_link(kubernetes_network)

    kubernetes_link.client.delete_namespaced_custom_object.assert_called_once_with(
        body=client.V1DeleteOptions(grace_period_seconds=0),
        grace_period_seconds=0,
        group="k8s.cni.cncf.io",
        name="netprefix-a",
        plural="network-attachment-definitions",
        namespace=default_link.lab.hash,
        version="v1"
    )


#
# TEST: get_links_api_objects_by_filters
#
def test_get_links_by_filters(kubernetes_link):
    kubernetes_link.get_links_api_objects_by_filters("lab_hash_value", "link_name_value")
    filters = ["app=kathara", "name=link_name_value"]

    kubernetes_link.client.list_namespaced_custom_object.called_once_with(
        group="k8s.cni.cncf.io",
        version="v1",
        namespace="lab_hash_value",
        plural="network-attachment-definitions",
        label_selector=",".join(filters),
        timeout_seconds=9999
    )


def test_get_links_by_filters_empty_filters(kubernetes_link):
    kubernetes_link.get_links_api_objects_by_filters()

    filters = ["app=kathara"]

    kubernetes_link.client.list_namespaced_custom_object.called_once_with(
        group="k8s.cni.cncf.io",
        version="v1",
        namespace="lab_hash_value",
        plural="network-attachment-definitions",
        label_selector=",".join(filters),
        timeout_seconds=9999
    )


def test_get_links_by_filters_only_lab_hash(kubernetes_link):
    kubernetes_link.get_links_api_objects_by_filters("lab_hash_value")

    filters = ["app=kathara", "lab_hash=lab_hash_value"]

    kubernetes_link.client.list_namespaced_custom_object.called_once_with(
        group="k8s.cni.cncf.io",
        version="v1",
        namespace="lab_hash_value",
        plural="network-attachment-definitions",
        label_selector=",".join(filters),
        timeout_seconds=9999
    )


def test_get_links_by_filters_only_link_name(kubernetes_link):
    kubernetes_link.get_links_api_objects_by_filters(None, "link_name_value")

    filters = ["app=kathara", "name=link_name_value"]

    kubernetes_link.client.list_namespaced_custom_object.called_once_with(
        group="k8s.cni.cncf.io",
        version="v1",
        namespace="lab_hash_value",
        plural="network-attachment-definitions",
        label_selector=",".join(filters),
        timeout_seconds=9999
    )


#
# TEST: undeploy
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink._undeploy_link")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_undeploy(mock_get_links_by_filters, mock_undeploy_link, kubernetes_network, kubernetes_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")
    mock_get_links_by_filters.return_value = [kubernetes_network, kubernetes_network, kubernetes_network]

    kubernetes_link.undeploy("lab_hash")

    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_undeploy_link.call_count == 3


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink._undeploy_link")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_undeploy_empty_lab(mock_get_links_by_filters, mock_undeploy_link, kubernetes_link):
    lab = Lab("Default scenario")

    mock_get_links_by_filters.return_value = []

    kubernetes_link.undeploy("lab_hash")

    mock_get_links_by_filters.called_once_with(lab.hash)
    assert not mock_undeploy_link.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink._undeploy_link")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_undeploy_selected_links(mock_get_links_by_filters, mock_undeploy_link, kubernetes_network, kubernetes_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")

    kubernetes_network_1 = copy.deepcopy(kubernetes_network)
    kubernetes_network_1["metadata"]["name"] = "netprefix-b"
    kubernetes_network_2 = copy.deepcopy(kubernetes_network)
    kubernetes_network_2["metadata"]["name"] = "netprefix-c"

    mock_get_links_by_filters.return_value = [kubernetes_network, kubernetes_network_1, kubernetes_network_2]

    kubernetes_link.undeploy("lab_hash", selected_links={"netprefix-b"})

    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_undeploy_link.call_count == 1


#
# TEST: wipe
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink._undeploy_link")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_wipe(mock_get_links_by_filters, mock_undeploy_link, kubernetes_link, kubernetes_network):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")

    mock_get_links_by_filters.return_value = [kubernetes_network, kubernetes_network, kubernetes_network]

    kubernetes_link.wipe()

    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_undeploy_link.call_count == 3


#
# TEST: get_links_stats
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash(mock_get_links_api_objects_by_filters, kubernetes_link,
                                  kubernetes_network):
    kubernetes_network['metadata']['name'] = "test_network"
    mock_get_links_api_objects_by_filters.return_value = [kubernetes_network]
    stat = next(kubernetes_link.get_links_stats(lab_hash="lab_hash"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name=None)
    assert stat['test_network']
    assert stat['test_network'].network_name == "test_network"


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_name(mock_get_links_api_objects_by_filters, kubernetes_link,
                                            kubernetes_network):
    kubernetes_network['metadata']['name'] = "test_network"
    mock_get_links_api_objects_by_filters.return_value = [kubernetes_network]
    next(kubernetes_link.get_links_stats(lab_hash="lab_hash", link_name="test_network"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name="test_network")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_not_found(mock_get_links_api_objects_by_filters, kubernetes_link,
                                                 kubernetes_network):
    kubernetes_network['metadata']['name'] = "test_network"
    mock_get_links_api_objects_by_filters.return_value = []
    with pytest.raises(LinkNotFoundError):
        next(kubernetes_link.get_links_stats(lab_hash="lab_hash"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_stats_lab_hash_link_name_not_found(mock_get_links_api_objects_by_filters, kubernetes_link,
                                                      kubernetes_network):
    kubernetes_network['metadata']['name'] = "test_network"
    mock_get_links_api_objects_by_filters.return_value = []
    with pytest.raises(LinkNotFoundError):
        next(kubernetes_link.get_links_stats(lab_hash="lab_hash", link_name="test_network"))
    mock_get_links_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", link_name="test_network")
