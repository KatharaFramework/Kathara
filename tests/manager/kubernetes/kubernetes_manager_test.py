import json
import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from kubernetes import client

sys.path.insert(0, './')

from src.Kathara.exceptions import NotSupportedError
from src.Kathara.manager.kubernetes.KubernetesMachine import KubernetesMachine
from src.Kathara.manager.kubernetes.KubernetesManager import KubernetesManager
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.utils import generate_urlsafe_hash
from src.Kathara.manager.kubernetes.stats.KubernetesMachineStats import KubernetesMachineStats
from src.Kathara.manager.kubernetes.stats.KubernetesLinkStats import KubernetesLinkStats


#
# FIXTURE
#
@pytest.fixture()
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_namespace(mock_kubernetes_namespace):
    mock_kubernetes_namespace.create = Mock()
    return mock_kubernetes_namespace


@pytest.fixture()
@mock.patch("kubernetes.client.api.apps_v1_api.AppsV1Api")
@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesConfigMap")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_machine(mock_kubernetes_namespace, mock_config_map, mock_core_v1_api, mock_apps_v1_api):
    return KubernetesMachine(mock_kubernetes_namespace)


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def kubernetes_manager(mock_setting_get_instance, kubernetes_namespace):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'manager': 'kubernetes',
        'device_prefix': 'devprefix'
    })
    kube_manager = KubernetesManager()
    kube_manager.k8s_namespace = kubernetes_namespace
    mock_setting_get_instance.return_value = mock_setting
    return kube_manager


@pytest.fixture()
def two_device_scenario():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc1.name, "B")
    lab.connect_machine_to_link(pc2.name, "A")
    return lab


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
def two_device_scenario():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc1.name, "B")
    lab.connect_machine_to_link(pc2.name, "A")
    return lab


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
def kubernetes_pod_1():
    networks = [
        {'name': 'a'},
        {'name': 'b'}
    ]

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": json.dumps(networks)},
                                       labels={"name": "pc1", "app": "kathara"}
                                       )
    pod_status = client.V1PodStatus(phase='Running')

    return client.V1Pod(
        metadata=pod_metadata,
        status=pod_status
    )


@pytest.fixture()
def kubernetes_pod_2():
    networks = [
        {'name': 'a'}
    ]

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": json.dumps(networks)},
                                       labels={"name": "pc2", "app": "kathara"}
                                       )
    pod_status = client.V1PodStatus(phase='Running')

    return client.V1Pod(
        metadata=pod_metadata,
        status=pod_status
    )


#
# TEST: deploy_lab
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab(mock_deploy_links, mock_deploy_machines, kubernetes_manager, two_device_scenario):
    kubernetes_manager.deploy_lab(two_device_scenario)
    mock_deploy_links.assert_called_once_with(two_device_scenario, selected_links=None)
    mock_deploy_machines.assert_called_once_with(two_device_scenario, selected_machines=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_selected_machines(mock_deploy_links, mock_deploy_machines, kubernetes_manager,
                                      two_device_scenario: Lab):
    kubernetes_manager.deploy_lab(two_device_scenario, selected_machines={"pc1"})

    mock_deploy_links.assert_called_once_with(two_device_scenario, selected_links={
        "A": two_device_scenario.get_or_new_link("A"),
        "B": two_device_scenario.get_or_new_link("B")
    })
    mock_deploy_machines.assert_called_once_with(two_device_scenario, selected_machines={"pc1"})


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_selected_machines_exception(mock_deploy_links, mock_deploy_machines, kubernetes_manager,
                                                two_device_scenario: Lab):
    with pytest.raises(Exception):
        kubernetes_manager.deploy_lab(two_device_scenario, selected_machines={"pc3"})
    assert not mock_deploy_machines.called
    assert not mock_deploy_links.called


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


#
# TEST: get_machines_stats
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_stats")
def test_get_machines_stats_lab_hash(mock_get_machines_stats, kubernetes_manager):
    kubernetes_manager.get_machines_stats(lab_hash="lab_hash")
    mock_get_machines_stats.assert_called_once_with(lab_hash="lab_hash", machine_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_stats")
def test_get_machines_stats_lab_name(mock_get_machines_stats, kubernetes_manager):
    kubernetes_manager.get_machines_stats(lab_name="lab_name")
    mock_get_machines_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name").lower(),
                                                    machine_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_stats")
def test_get_machines_stats_no_hash_no_name(mock_get_machines_stats, kubernetes_manager):
    kubernetes_manager.get_machines_stats(all_users=True)
    mock_get_machines_stats.assert_called_once_with(lab_hash=None, machine_name=None)


#
# TEST: get_machine_stats
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_stats")
def test_get_machine_stats_lab_hash(mock_get_machines_stats, default_device, kubernetes_manager):
    mock_get_machines_stats.return_value = iter([{"test_device": KubernetesMachineStats(default_device.api_object)}])
    next(kubernetes_manager.get_machine_stats(machine_name="test_device", lab_hash="lab_hash"))
    mock_get_machines_stats.assert_called_once_with(lab_hash="lab_hash", machine_name="test_device")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_stats")
def test_get_machine_stats_lab_name(mock_get_machines_stats, default_device, kubernetes_manager):
    mock_get_machines_stats.return_value = iter([{"test_device": KubernetesMachineStats(default_device.api_object)}])
    next(kubernetes_manager.get_machine_stats(machine_name="test_device", lab_name="lab_name"))
    mock_get_machines_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name").lower(),
                                                    machine_name="test_device")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_stats")
def test_get_machine_stats_no_hash_no_name(mock_get_machines_stats, kubernetes_manager):
    mock_get_machines_stats.return_value = iter([])
    with pytest.raises(Exception):
        next(kubernetes_manager.get_machine_stats(machine_name="test_device"))
    assert not mock_get_machines_stats.called


#
# TESTS: get_links_stats
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_links_stats_lab_hash(mock_get_links_stats, kubernetes_manager):
    kubernetes_manager.get_links_stats(lab_hash="lab_hash")
    mock_get_links_stats.assert_called_once_with(lab_hash="lab_hash", link_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_links_stats_lab_name(mock_get_links_stats, kubernetes_manager):
    kubernetes_manager.get_links_stats(lab_name="lab_name")
    mock_get_links_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name").lower(), link_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_links_stats_no_lab_hash(mock_get_links_stats, kubernetes_manager):
    kubernetes_manager.get_links_stats()
    mock_get_links_stats.assert_called_once_with(lab_hash=None, link_name=None)


#
# TESTS: get_link_stats
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_link_stats_lab_hash(mock_get_links_stats, kubernetes_network, kubernetes_manager):
    mock_get_links_stats.return_value = iter([{"test_network": KubernetesLinkStats(kubernetes_network)}])
    next(kubernetes_manager.get_link_stats(link_name="test_network", lab_hash="lab_hash"))
    mock_get_links_stats.assert_called_once_with(lab_hash="lab_hash", link_name="test_network")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_link_stats_lab_name(mock_get_links_stats, kubernetes_network, kubernetes_manager):
    mock_get_links_stats.return_value = iter([{"test_network": KubernetesLinkStats(kubernetes_network)}])
    next(kubernetes_manager.get_links_stats(link_name="test_network", lab_name="lab_name"))
    mock_get_links_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name").lower(),
                                                 link_name="test_network")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_link_stats_no_lab_hash_and_no_name(mock_get_links_stats, kubernetes_manager):
    with pytest.raises(Exception):
        next(kubernetes_manager.get_link_stats(link_name="test_network"))
    assert not mock_get_links_stats.called
