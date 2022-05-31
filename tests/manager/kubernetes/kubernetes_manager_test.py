import sys
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.kubernetes.KubernetesMachine import KubernetesMachine
from src.Kathara.manager.kubernetes.KubernetesManager import KubernetesManager
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.utils import generate_urlsafe_hash
from src.Kathara.manager.kubernetes.KubernetesLink import KubernetesLink


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

    def dict(self):
        return {}

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
@mock.patch("kubernetes.client.api.apps_v1_api.AppsV1Api")
@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesConfigMap")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_machine(mock_kubernetes_namespace, mock_config_map, mock_core_v1_api, mock_apps_v1_api):
    return KubernetesMachine(mock_kubernetes_namespace)


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesConfig.KubernetesConfig")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_manager(mock_kubernetes_namespace, mock_kubernetes_link, mock_kubernetes_machine,
                       mock_kubernetes_load_config, mock_setting_get_instance):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'manager': 'kubernetes',
        'device_prefix': 'devprefix'
    })
    mock_setting_get_instance.return_value = mock_setting
    return KubernetesManager()


@pytest.fixture()
@mock.patch("kubernetes.client.models.v1_deployment.V1Deployment")
def default_device(mock_kubernetes_deployment):
    device = Machine(Lab("default_scenario"), "test_device")
    device.add_meta("exec", "ls")
    device.add_meta("mem", "64m")
    device.add_meta("cpus", "2")
    device.add_meta("image", "kathara/test")
    device.add_meta("bridged", False)
    device.add_meta('real_name', "devprefix-test-device-ec84ad3b")

    device.api_object = mock_kubernetes_deployment

    return device


@pytest.fixture()
def default_link():
    from src.Kathara.model.Link import Link
    return Link(Lab("default_scenario"), "A")


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


@pytest.fixture()
@mock.patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi")
@mock.patch("kubernetes.client.Configuration")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_link(kubernetes_namespace_mock, config_mock, _):
    config_mock.get_default_copy.return_value = FakeConfig()

    return KubernetesLink(kubernetes_namespace_mock)


#
# TEST: get_machine_api_objects
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_hash(mock_get_machines_api_objects, kubernetes_manager, default_device):
    default_device.api_object.name = "default_device"
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machine_api_object(machine_name="default_device", lab_hash="lab_hash_value")
    mock_get_machines_api_objects.assert_called_once_with(machine_name="default_device", lab_hash="lab_hash_value")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_name(mock_get_machines_api_objects, kubernetes_manager, default_device):
    default_device.api_object.name = "default_device"
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machine_api_object(machine_name="default_device", lab_name="lab_name")
    mock_get_machines_api_objects.assert_called_once_with(machine_name="default_device",
                                                          lab_hash=generate_urlsafe_hash("lab_name").lower())


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_hash_and_name(mock_get_machines_api_objects, kubernetes_manager, default_device):
    default_device.api_object.name = "default_device"
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machine_api_object(machine_name="default_device", lab_name="lab_name", lab_hash="lab_hash")
    mock_get_machines_api_objects.assert_called_once_with(machine_name="default_device",
                                                          lab_hash=generate_urlsafe_hash("lab_name").lower())


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_no_hash_no_name(mock_get_machines_api_objects, kubernetes_manager, default_device):
    default_device.api_object.name = "default_device"
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    with pytest.raises(Exception):
        kubernetes_manager.get_machine_api_object(machine_name="default_device")
    assert not mock_get_machines_api_objects.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_hash_device_not_found(mock_get_machines_api_objects, kubernetes_manager):
    mock_get_machines_api_objects.return_value = []
    with pytest.raises(Exception):
        kubernetes_manager.get_machine_api_object(lab_hash="lab_hash_value", machine_name="default_device")
    mock_get_machines_api_objects.assert_called_once_with(machine_name="default_device", lab_hash="lab_hash_value")


#
# TEST: get_machines_api_objects
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_hash(mock_get_machines_api_objects, kubernetes_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machines_api_objects(lab_hash="lab_hash_value")
    mock_get_machines_api_objects.assert_called_once_with(lab_hash="lab_hash_value")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_name(mock_get_machines_api_objects, kubernetes_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machines_api_objects(lab_name="lab_name")
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name").lower())


#
# TEST: get_links_api_objects
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_hash(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_links_api_objects(lab_hash="lab_hash_value")
    mock_get_links_api_objects.assert_called_once_with(lab_hash="lab_hash_value")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_name(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_links_api_objects(lab_name="lab_name")
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name").lower())


#
# TEST: get_link_api_object
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_hash(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_link_api_object(link_name="test_network", lab_hash="lab_hash_value")
    mock_get_links_api_objects.assert_called_once_with(link_name="test_network", lab_hash="lab_hash_value")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_name(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_link_api_object(link_name="test_network", lab_name="lab_name")
    mock_get_links_api_objects.assert_called_once_with(link_name="test_network",
                                                       lab_hash=generate_urlsafe_hash("lab_name").lower())


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_hash_and_name(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_link_api_object(link_name="test_network", lab_name="lab_name", lab_hash="lab_hash")
    mock_get_links_api_objects.assert_called_once_with(link_name="test_network",
                                                       lab_hash=generate_urlsafe_hash("lab_name").lower())


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_no_hash_no_name(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    with pytest.raises(Exception):
        kubernetes_manager.get_link_api_object(link_name="test_network")
    assert not mock_get_links_api_objects.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_hash_cd_not_found(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = []
    with pytest.raises(Exception):
        kubernetes_manager.get_link_api_object(link_name="test_network", lab_hash="lab_hash_value")
    mock_get_links_api_objects.assert_called_once_with(link_name="test_network", lab_hash="lab_hash_value")
