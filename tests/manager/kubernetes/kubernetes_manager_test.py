import json
import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from kubernetes import client

sys.path.insert(0, './')

from src.Kathara.exceptions import NotSupportedError, MachineNotFoundError, LabNotFoundError, InvocationError, \
    LinkNotFoundError
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
@mock.patch("src.Kathara.manager.kubernetes.KubernetesSecret")
def kubernetes_secret(mock_kubernetes_secret):
    mock_kubernetes_secret.create = Mock()
    return mock_kubernetes_secret


@pytest.fixture()
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_machine(mock_kubernetes_namespace):
    return KubernetesMachine(mock_kubernetes_namespace)


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def kubernetes_manager(mock_setting_get_instance, kubernetes_namespace, kubernetes_secret):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'manager': 'kubernetes',
        'device_prefix': 'devprefix',
        'net_prefix': 'netprefix'
    })
    kube_manager = KubernetesManager()
    kube_manager.k8s_namespace = kubernetes_namespace
    kube_manager.k8s_secret = kubernetes_secret
    mock_setting_get_instance.return_value = mock_setting
    return kube_manager


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
def three_device_scenario():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    pc3 = lab.get_or_new_machine("pc3", **{'image': 'kathara/test3'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc1.name, "B")
    lab.connect_machine_to_link(pc2.name, "A")
    lab.connect_machine_to_link(pc3.name, "A")
    lab.connect_machine_to_link(pc3.name, "C")
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
        {'name': 'netprefix-a'},
        {'name': 'netprefix-b'}
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
        {'name': 'netprefix-a'}
    ]

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": json.dumps(networks)},
                                       labels={"name": "pc2", "app": "kathara"}
                                       )

    pod_container_resources = client.V1ResourceRequirements(
        limits={'memory': '64m', 'cpu': '1000'}
    )
    pod_container_env = [
        client.V1EnvVar('_MEGALOS_SHELL', '/bin/bash'),
        client.V1EnvVar('test', 'path')
    ]
    pod_container_ports = [
        client.V1ContainerPort(name="port", container_port=56, host_port=3001, protocol="UDP")
    ]

    pod_container = client.V1Container(
        name="pc1_container",
        image="docker.io/test_image2",
        resources=pod_container_resources,
        env=pod_container_env,
        ports=pod_container_ports
    )
    pod_spec = client.V1PodSpec(
        containers=[pod_container]
    )

    pod_status = client.V1PodStatus(phase='Running')

    return client.V1Pod(
        metadata=pod_metadata,
        spec=pod_spec,
        status=pod_status
    )


@pytest.fixture()
def kubernetes_pod_3():
    networks = [
        {'name': 'netprefix-c'},
        {'name': 'netprefix-d'},
    ]

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": json.dumps(networks)},
                                       labels={"name": "pc3", "app": "kathara"}
                                       )

    pod_container_resources = client.V1ResourceRequirements(
        limits={'memory': '64m', 'cpu': '1000'}
    )
    pod_container_env = [
        client.V1EnvVar('_MEGALOS_SHELL', '/bin/bash'),
        client.V1EnvVar('test', 'path')
    ]
    pod_container_ports = [
        client.V1ContainerPort(name="port", container_port=57, host_port=3002, protocol="UDP")
    ]

    pod_container = client.V1Container(
        name="pc1_container",
        image="docker.io/test_image3",
        resources=pod_container_resources,
        env=pod_container_env,
        ports=pod_container_ports
    )
    pod_spec = client.V1PodSpec(
        containers=[pod_container]
    )

    pod_status = client.V1PodStatus(phase='Running')

    return client.V1Pod(
        metadata=pod_metadata,
        spec=pod_spec,
        status=pod_status
    )


@pytest.fixture()
def kubernetes_empty_pod():
    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": json.dumps([])},
                                       labels={"name": "pc2", "app": "kathara"}
                                       )

    pod_container_resources = client.V1ResourceRequirements()
    pod_container_env = [client.V1EnvVar('_MEGALOS_SHELL', '/bin/bash')]

    pod_container = client.V1Container(
        name="pc1_container",
        image="docker.io/test_image",
        resources=pod_container_resources,
        env=pod_container_env,
        ports=[]
    )
    pod_spec = client.V1PodSpec(
        containers=[pod_container]
    )

    pod_status = client.V1PodStatus(phase='Running')

    return client.V1Pod(
        metadata=pod_metadata,
        spec=pod_spec,
        status=pod_status
    )


@pytest.fixture()
def two_device_scenario(kubernetes_pod_1, kubernetes_pod_2):
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc1.api_object = kubernetes_pod_1
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    pc2.api_object = kubernetes_pod_2
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc1.name, "B")
    lab.connect_machine_to_link(pc2.name, "A")
    return lab


#
# TEST: deploy_lab
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab(mock_deploy_links, mock_deploy_machines, kubernetes_manager, two_device_scenario):
    kubernetes_manager.deploy_lab(two_device_scenario)
    kubernetes_manager.k8s_namespace.create.assert_called_once_with(two_device_scenario)
    kubernetes_manager.k8s_secret.create.assert_called_once_with(two_device_scenario)
    mock_deploy_links.assert_called_once_with(two_device_scenario, selected_links=None, excluded_links=None)
    mock_deploy_machines.assert_called_once_with(two_device_scenario, selected_machines=None, excluded_machines=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace.KubernetesNamespace.create")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_selected_machines(mock_deploy_links, mock_deploy_machines, mock_namespace_create,
                                      kubernetes_manager, two_device_scenario: Lab):
    kubernetes_manager.deploy_lab(two_device_scenario, selected_machines={"pc1"})
    kubernetes_manager.k8s_namespace.create.assert_called_once_with(two_device_scenario)
    kubernetes_manager.k8s_secret.create.assert_called_once_with(two_device_scenario)
    mock_deploy_links.assert_called_once_with(two_device_scenario, selected_links={"A", "B"}, excluded_links=None)
    mock_deploy_machines.assert_called_once_with(two_device_scenario, selected_machines={"pc1"}, excluded_machines=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_selected_machines_exception(mock_deploy_links, mock_deploy_machines, kubernetes_manager,
                                                two_device_scenario: Lab):
    with pytest.raises(MachineNotFoundError):
        kubernetes_manager.deploy_lab(two_device_scenario, selected_machines={"pc3"})
    assert not kubernetes_manager.k8s_namespace.create.called
    assert not kubernetes_manager.k8s_secret.create.called
    assert not mock_deploy_machines.called
    assert not mock_deploy_links.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_excluded_machines(mock_deploy_links, mock_deploy_machines, kubernetes_manager,
                                      three_device_scenario: Lab):
    kubernetes_manager.deploy_lab(three_device_scenario, excluded_machines={"pc3"})
    kubernetes_manager.k8s_namespace.create.assert_called_once_with(three_device_scenario)
    kubernetes_manager.k8s_secret.create.assert_called_once_with(three_device_scenario)
    mock_deploy_links.assert_called_once_with(three_device_scenario, selected_links=None, excluded_links={'C'})
    mock_deploy_machines.assert_called_once_with(
        three_device_scenario, selected_machines=None, excluded_machines={"pc3"}
    )


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_excluded_machines_exception(mock_deploy_links, mock_deploy_machines, kubernetes_manager,
                                                two_device_scenario: Lab):
    with pytest.raises(MachineNotFoundError):
        kubernetes_manager.deploy_lab(two_device_scenario, excluded_machines={"pc3"})
    assert not kubernetes_manager.k8s_namespace.create.called
    assert not kubernetes_manager.k8s_secret.create.called
    assert not mock_deploy_machines.called
    assert not mock_deploy_links.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_lab_selected_and_excluded_machines(mock_deploy_links, mock_deploy_machines, kubernetes_manager,
                                                   three_device_scenario: Lab):
    with pytest.raises(InvocationError):
        kubernetes_manager.deploy_lab(
            three_device_scenario, selected_machines={"pc1", "pc2"}, excluded_machines={"pc2"}
        )
    assert not kubernetes_manager.k8s_namespace.create.called
    assert not kubernetes_manager.k8s_secret.create.called
    assert not mock_deploy_machines.called
    assert not mock_deploy_links.called


#
# TEST: deploy_machine
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.deploy_machines")
def test_deploy_machine(mock_deploy_machines, mock_deploy_links, kubernetes_manager,
                        default_device, default_link):
    default_device.add_interface(default_link)

    kubernetes_manager.deploy_machine(default_device)
    kubernetes_manager.k8s_namespace.create.assert_called_once_with(default_device.lab)
    kubernetes_manager.k8s_secret.create.assert_called_once_with(default_device.lab)
    mock_deploy_links.assert_called_once_with(default_device.lab, selected_links={default_link.name})
    mock_deploy_machines.assert_called_once_with(default_device.lab, selected_machines={default_device.name})


def test_deploy_machine_no_lab(kubernetes_manager, default_device):
    default_device.lab = None

    with pytest.raises(LabNotFoundError):
        kubernetes_manager.deploy_machine(default_device)


#
# TEST: deploy_link
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.deploy_links")
def test_deploy_link(mock_deploy_links, mock_setting_get_instance, kubernetes_manager, default_link):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = mock_setting

    kubernetes_manager.deploy_link(default_link)

    kubernetes_manager.k8s_namespace.create.assert_called_once_with(default_link.lab)
    mock_deploy_links.assert_called_once_with(default_link.lab, selected_links={default_link.name})


def test_deploy_link_no_lab(kubernetes_manager, default_link):
    default_link.lab = None

    with pytest.raises(LabNotFoundError):
        kubernetes_manager.deploy_link(default_link)


#
# TEST: connect_machine_to_link
#
def test_connect_machine_to_link_not_supported(kubernetes_manager, default_device, default_link):
    with pytest.raises(NotSupportedError):
        kubernetes_manager.connect_machine_to_link(default_device, default_link)


#
# TEST: disconnect_machine_from_link
#
def test_disconnect_machine_from_link_not_supported(kubernetes_manager, default_device, default_link):
    with pytest.raises(NotSupportedError):
        kubernetes_manager.disconnect_machine_from_link(default_device, default_link)


#
# TEST: undeploy_machine
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_machine(mock_machine_undeploy, mock_link_undeploy, mock_get_machines_api_objects,
                          mock_setting_get_instance, kubernetes_manager, default_device, default_link):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = mock_setting

    default_device.add_interface(default_link)

    mock_get_machines_api_objects.return_value = []

    kubernetes_manager.undeploy_machine(default_device)

    mock_machine_undeploy.assert_called_once_with(default_device.lab.hash, selected_machines={default_device.name})
    mock_link_undeploy.assert_called_once_with(default_device.lab.hash, selected_links={'netprefix-a'})
    kubernetes_manager.k8s_namespace.undeploy.assert_called_once_with(lab_hash=default_device.lab.hash)


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_machine_two_machines(mock_machine_undeploy, mock_link_undeploy, mock_get_machines_api_objects,
                                       mock_setting_get_instance, kubernetes_manager, two_device_scenario):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = mock_setting

    device_1 = two_device_scenario.get_or_new_machine('pc1')
    device_2 = two_device_scenario.get_or_new_machine('pc2')

    mock_get_machines_api_objects.return_value = [device_2.api_object]

    kubernetes_manager.undeploy_machine(device_1)

    mock_machine_undeploy.assert_called_with(two_device_scenario.hash, selected_machines={device_1.name})
    mock_link_undeploy.assert_called_with(two_device_scenario.hash, selected_links={'netprefix-b'})
    assert not kubernetes_manager.k8s_namespace.undeploy.called

    mock_get_machines_api_objects.return_value = []

    kubernetes_manager.undeploy_machine(device_2)

    mock_machine_undeploy.assert_called_with(two_device_scenario.hash, selected_machines={device_2.name})
    mock_link_undeploy.assert_called_with(two_device_scenario.hash, selected_links={'netprefix-a'})
    kubernetes_manager.k8s_namespace.undeploy.assert_called_once_with(lab_hash=two_device_scenario.hash)


def test_undeploy_machine_no_lab(kubernetes_manager, default_device):
    default_device.lab = None

    with pytest.raises(LabNotFoundError):
        kubernetes_manager.undeploy_machine(default_device)


#
# TEST: undeploy_link
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
def test_undeploy_link(mock_link_undeploy, mock_get_machines_api_objects, mock_setting_get_instance, kubernetes_manager,
                       default_link):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = mock_setting

    mock_get_machines_api_objects.return_value = []

    kubernetes_manager.undeploy_link(default_link)

    mock_link_undeploy.assert_called_once_with(default_link.lab.hash, selected_links={'netprefix-a'})


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
def test_undeploy_link_machine_running(mock_link_undeploy, mock_get_machines_api_objects, mock_setting_get_instance,
                                       kubernetes_manager, default_link, kubernetes_pod_2):
    mock_setting = Mock()
    mock_setting.configure_mock(**{
        'net_prefix': 'netprefix'
    })
    mock_setting_get_instance.return_value = mock_setting

    mock_get_machines_api_objects.return_value = [kubernetes_pod_2]

    kubernetes_manager.undeploy_link(default_link)

    assert not mock_link_undeploy.called


def test_undeploy_link_no_lab(kubernetes_manager, default_link):
    default_link.lab = None
    with pytest.raises(LabNotFoundError):
        kubernetes_manager.undeploy_link(default_link)


#
# TEST: undeploy_lab
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_lab(mock_undeploy_machine, mock_undeploy_link, kubernetes_manager):
    kubernetes_manager.undeploy_lab('lab_hash')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines=None, excluded_machines=None)
    mock_undeploy_link.assert_called_once_with('lab_hash', selected_links=None)
    kubernetes_manager.k8s_namespace.undeploy.assert_called_once_with(lab_hash='lab_hash')


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_lab_selected_machines(mock_undeploy_machine, mock_undeploy_link,
                                        mock_get_machines_api_objects, mock_get_links_api_objects, kubernetes_manager,
                                        kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3):
    mock_get_links_api_objects.return_value = [{'metadata': {'name': 'netprefix-a'}},
                                               {'metadata': {'name': 'netprefix-b'}},
                                               {'metadata': {'name': 'netprefix-c'}},
                                               {'metadata': {'name': 'netprefix-d'}}]
    mock_get_machines_api_objects.return_value = [kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3]

    kubernetes_manager.undeploy_lab('lab_hash', selected_machines={'pc1'})
    mock_get_links_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_get_machines_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines={'pc1'}, excluded_machines=None)
    mock_undeploy_link.assert_called_once_with('lab_hash', selected_links={'netprefix-b'})
    assert not kubernetes_manager.k8s_namespace.undeploy.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_lab_selected_machines_delete_ns(mock_undeploy_machine, mock_undeploy_link,
                                                  mock_get_machines_api_objects,
                                                  mock_get_links_api_objects, kubernetes_manager,
                                                  kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3):
    mock_get_links_api_objects.return_value = [{'metadata': {'name': 'netprefix-a'}},
                                               {'metadata': {'name': 'netprefix-b'}},
                                               {'metadata': {'name': 'netprefix-c'}},
                                               {'metadata': {'name': 'netprefix-d'}}]
    mock_get_machines_api_objects.return_value = [kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3]

    kubernetes_manager.undeploy_lab('lab_hash', selected_machines={'pc1', 'pc2', 'pc3'})
    mock_get_links_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_get_machines_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_undeploy_machine.assert_called_once_with(
        'lab_hash', selected_machines={'pc1', 'pc2', 'pc3'}, excluded_machines=None
    )
    mock_undeploy_link.assert_called_once_with(
        'lab_hash', selected_links={'netprefix-a', 'netprefix-b', 'netprefix-c', 'netprefix-d'}
    )
    kubernetes_manager.k8s_namespace.undeploy.assert_called_once_with(lab_hash='lab_hash')


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_lab_excluded_machines(mock_undeploy_machine, mock_undeploy_link,
                                        mock_get_machines_api_objects, mock_get_links_api_objects, kubernetes_manager,
                                        kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3):
    mock_get_links_api_objects.return_value = [{'metadata': {'name': 'netprefix-a'}},
                                               {'metadata': {'name': 'netprefix-b'}},
                                               {'metadata': {'name': 'netprefix-c'}},
                                               {'metadata': {'name': 'netprefix-d'}}]
    mock_get_machines_api_objects.return_value = [kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3]

    kubernetes_manager.undeploy_lab('lab_hash', excluded_machines={'pc3'})
    mock_get_links_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_get_machines_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines=None, excluded_machines={'pc3'})
    mock_undeploy_link.assert_called_once_with('lab_hash', selected_links={'netprefix-a', 'netprefix-b'})
    assert not kubernetes_manager.k8s_namespace.undeploy.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_lab_excluded_machines_delete_ns(mock_undeploy_machine, mock_undeploy_link,
                                                  mock_get_machines_api_objects, mock_get_links_api_objects,
                                                  kubernetes_manager,
                                                  kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3):
    mock_get_links_api_objects.return_value = []
    mock_get_machines_api_objects.return_value = []

    kubernetes_manager.undeploy_lab('lab_hash', excluded_machines={'pc3'})
    mock_get_links_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_get_machines_api_objects.assert_called_once_with(lab_hash='lab_hash')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines=None, excluded_machines={'pc3'})
    mock_undeploy_link.assert_called_once_with('lab_hash', selected_links=set())
    kubernetes_manager.k8s_namespace.undeploy.assert_called_once_with(lab_hash='lab_hash')


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.undeploy")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.undeploy")
def test_undeploy_lab_selected_and_excluded_machines(mock_undeploy_machine, mock_undeploy_link, kubernetes_manager,
                                                     kubernetes_pod_1, kubernetes_pod_2, kubernetes_pod_3):
    with pytest.raises(InvocationError):
        kubernetes_manager.undeploy_lab(
            'lab_hash', selected_machines={'pc1', 'pc2'}, excluded_machines={'pc2'}
        )
    assert not mock_undeploy_machine.called
    assert not mock_undeploy_link.called
    assert not kubernetes_manager.k8s_namespace.undeploy.called


#
# TEST: connect_tty
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.connect")
def test_connect_tty_lab_hash(mock_connect, kubernetes_manager, default_device):
    kubernetes_manager.connect_tty(default_device.name,
                                   lab_hash=default_device.lab.hash)

    mock_connect.assert_called_once_with(lab_hash=default_device.lab.hash.lower(),
                                         machine_name=default_device.name,
                                         shell=None,
                                         logs=False)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.connect")
def test_connect_tty_lab_name(mock_connect, kubernetes_manager, default_device):
    kubernetes_manager.connect_tty(default_device.name,
                                   lab_name=default_device.lab.name)

    mock_connect.assert_called_once_with(lab_hash=generate_urlsafe_hash(default_device.lab.name).lower(),
                                         machine_name=default_device.name,
                                         shell=None,
                                         logs=False)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.connect")
def test_connect_tty_lab_obj(mock_connect, kubernetes_manager, default_device,
                             two_device_scenario):
    kubernetes_manager.connect_tty(default_device.name,
                                   lab=two_device_scenario)

    mock_connect.assert_called_once_with(lab_hash=two_device_scenario.hash.lower(),
                                         machine_name=default_device.name,
                                         shell=None,
                                         logs=False)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.connect")
def test_connect_tty_custom_shell(mock_connect, kubernetes_manager, default_device):
    kubernetes_manager.connect_tty(default_device.name,
                                   lab_hash=default_device.lab.hash,
                                   shell='/usr/bin/zsh')

    mock_connect.assert_called_once_with(lab_hash=default_device.lab.hash.lower(),
                                         machine_name=default_device.name,
                                         shell='/usr/bin/zsh',
                                         logs=False)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.connect")
def test_connect_tty_with_logs(mock_connect, kubernetes_manager, default_device):
    kubernetes_manager.connect_tty(default_device.name,
                                   lab_hash=default_device.lab.hash,
                                   logs=True)

    mock_connect.assert_called_once_with(lab_hash=default_device.lab.hash.lower(),
                                         machine_name=default_device.name,
                                         shell=None,
                                         logs=True)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.connect")
def test_connect_tty_invocation_error(mock_connect, kubernetes_manager, default_device):
    with pytest.raises(InvocationError):
        kubernetes_manager.connect_tty(default_device.name)

    assert not mock_connect.called


#
# TEST: exec
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.exec")
def test_exec_lab_hash(mock_exec, kubernetes_manager, default_device):
    kubernetes_manager.exec(default_device.name, ["test", "command"], lab_hash=default_device.lab.hash)

    mock_exec.assert_called_once_with(
        default_device.lab.hash.lower(),
        default_device.name,
        ["test", "command"],
        stderr=True,
        tty=False,
        is_stream=True
    )


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.exec")
def test_exec_lab_name(mock_exec, kubernetes_manager, default_device):
    kubernetes_manager.exec(default_device.name, ["test", "command"], lab_name=default_device.lab.name)

    mock_exec.assert_called_once_with(
        generate_urlsafe_hash(default_device.lab.name).lower(),
        default_device.name,
        ["test", "command"],
        stderr=True,
        tty=False,
        is_stream=True
    )


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.exec")
def test_exec_lab_obj(mock_exec, kubernetes_manager, default_device, two_device_scenario):
    kubernetes_manager.exec(default_device.name, ["test", "command"], lab=two_device_scenario)

    mock_exec.assert_called_once_with(
        two_device_scenario.hash.lower(),
        default_device.name,
        ["test", "command"],
        stderr=True,
        tty=False,
        is_stream=True
    )


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.exec")
def test_exec_wait(mock_exec, kubernetes_manager, default_device):
    kubernetes_manager.exec(default_device.name, ["test", "command"], lab_hash=default_device.lab.hash, wait=True)

    mock_exec.assert_called_once_with(
        default_device.lab.hash.lower(),
        default_device.name,
        ["test", "command"],
        stderr=True,
        tty=False,
        is_stream=True
    )


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.exec")
def test_exec_invocation_error(mock_exec, kubernetes_manager, default_device):
    with pytest.raises(InvocationError):
        kubernetes_manager.exec(default_device.name, ["test", "command"])

    assert not mock_exec.called


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
def test_get_machine_api_object_lab_obj(mock_get_machines_api_objects, kubernetes_manager, default_device,
                                        two_device_scenario):
    default_device.api_object.name = "default_device"
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machine_api_object(machine_name="default_device", lab=two_device_scenario)
    mock_get_machines_api_objects.assert_called_once_with(machine_name="default_device",
                                                          lab_hash=two_device_scenario.hash.lower())


def test_get_machine_api_object_lab_hash_and_name(kubernetes_manager, default_device):
    with pytest.raises(InvocationError):
        kubernetes_manager.get_machine_api_object(machine_name="default_device", lab_name="lab_name",
                                                  lab_hash="lab_hash")


def test_get_machine_api_object_lab_hash_and_name_and_obj(kubernetes_manager, default_device, two_device_scenario):
    with pytest.raises(InvocationError):
        kubernetes_manager.get_machine_api_object(machine_name="default_device", lab_name="lab_name",
                                                  lab_hash="lab_hash", lab=two_device_scenario)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_invocation_error(mock_get_machines_api_objects, kubernetes_manager, default_device):
    default_device.api_object.name = "default_device"
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    with pytest.raises(InvocationError):
        kubernetes_manager.get_machine_api_object(machine_name="default_device")
    assert not mock_get_machines_api_objects.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_hash_device_not_found(mock_get_machines_api_objects, kubernetes_manager):
    mock_get_machines_api_objects.return_value = []
    with pytest.raises(MachineNotFoundError):
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


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_obj(mock_get_machines_api_objects, kubernetes_manager, default_device,
                                          two_device_scenario):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    kubernetes_manager.get_machines_api_objects(lab=two_device_scenario)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=two_device_scenario.hash.lower())


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


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_obj(mock_get_links_api_objects, kubernetes_manager, kubernetes_network,
                                       two_device_scenario):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_links_api_objects(lab=two_device_scenario)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=two_device_scenario.hash.lower())


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
def test_get_link_api_object_lab_obj(mock_get_links_api_objects, kubernetes_manager, kubernetes_network,
                                     two_device_scenario):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    kubernetes_manager.get_link_api_object(link_name="test_network", lab=two_device_scenario)
    mock_get_links_api_objects.assert_called_once_with(link_name="test_network",
                                                       lab_hash=two_device_scenario.hash.lower())


def test_get_link_api_object_lab_hash_and_name_and_obj(kubernetes_manager, kubernetes_network, two_device_scenario):
    with pytest.raises(InvocationError):
        kubernetes_manager.get_link_api_object(link_name="test_network", lab_name="lab_name", lab_hash="lab_hash",
                                               lab=two_device_scenario)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_invocation_error(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = [kubernetes_network]
    with pytest.raises(InvocationError):
        kubernetes_manager.get_link_api_object(link_name="test_network")
    assert not mock_get_links_api_objects.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_hash_cd_not_found(mock_get_links_api_objects, kubernetes_manager, kubernetes_network):
    mock_get_links_api_objects.return_value = []
    with pytest.raises(LinkNotFoundError):
        kubernetes_manager.get_link_api_object(link_name="test_network", lab_hash="lab_hash_value")
    mock_get_links_api_objects.assert_called_once_with(link_name="test_network", lab_hash="lab_hash_value")


#
# TESTS: get_lab_from_api
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_links_api_objects")
def test_get_lab_from_api_lab_name_all_info(mock_get_links_api_objects, mock_get_machines_api_objects,
                                            kubernetes_pod_2, kubernetes_network, kubernetes_manager):
    mock_get_machines_api_objects.return_value = [kubernetes_pod_2]
    mock_get_links_api_objects.return_value = [kubernetes_network]

    lab = kubernetes_manager.get_lab_from_api(lab_name="lab_test")
    assert len(lab.machines) == 1

    assert kubernetes_pod_2.metadata.labels["name"] in lab.machines
    reconstructed_device = lab.get_or_new_machine(kubernetes_pod_2.metadata.labels["name"])
    assert "privileged" not in reconstructed_device.meta
    assert reconstructed_device.meta["image"] == "test_image2"
    assert reconstructed_device.meta["shell"] == "/bin/bash"
    assert reconstructed_device.meta["mem"] == "64M"
    assert reconstructed_device.meta["cpu"] == 1.0
    assert reconstructed_device.meta["envs"]["test"] == "path"
    assert reconstructed_device.meta["ports"][(3001, "udp")] == 56
    assert reconstructed_device.meta["sysctls"] == {}
    assert len(lab.links) == 1
    assert kubernetes_network["metadata"]["labels"]["name"] in lab.links


@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_links_api_objects")
def test_get_lab_from_api_lab_hash_all_info(mock_get_links_api_objects, mock_get_machines_api_objects,
                                            kubernetes_pod_2, kubernetes_network, kubernetes_manager):
    mock_get_machines_api_objects.return_value = [kubernetes_pod_2]
    mock_get_links_api_objects.return_value = [kubernetes_network]

    lab = kubernetes_manager.get_lab_from_api(lab_hash="lab_hash")

    assert lab.hash == "lab_hash"
    assert lab.name == "reconstructed_lab"
    assert len(lab.machines) == 1

    assert kubernetes_pod_2.metadata.labels["name"] in lab.machines
    reconstructed_device = lab.get_or_new_machine(kubernetes_pod_2.metadata.labels["name"])
    assert "privileged" not in reconstructed_device.meta
    assert reconstructed_device.meta["image"] == "test_image2"
    assert reconstructed_device.meta["shell"] == "/bin/bash"
    assert reconstructed_device.meta["mem"] == "64M"
    assert reconstructed_device.meta["cpu"] == 1.0
    assert reconstructed_device.meta["envs"]["test"] == "path"
    assert reconstructed_device.meta["ports"][(3001, "udp")] == 56
    assert reconstructed_device.meta["sysctls"] == {}
    assert len(lab.links) == 1
    assert kubernetes_network["metadata"]["labels"]["name"] in lab.links


@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_links_api_objects")
def test_get_lab_from_api_lab_name_empty_meta(mock_get_links_api_objects, mock_get_machines_api_objects,
                                              kubernetes_empty_pod, kubernetes_manager):
    mock_get_machines_api_objects.return_value = [kubernetes_empty_pod]
    mock_get_links_api_objects.return_value = []

    lab = kubernetes_manager.get_lab_from_api(lab_name="lab_test")
    assert len(lab.machines) == 1
    assert kubernetes_empty_pod.metadata.labels["name"] in lab.machines
    reconstructed_device = lab.get_or_new_machine(kubernetes_empty_pod.metadata.labels["name"])
    assert "privileged" not in reconstructed_device.meta
    assert reconstructed_device.meta["image"] == "test_image"
    assert reconstructed_device.meta["shell"] == "/bin/bash"
    assert "mem" not in reconstructed_device.meta
    assert "cpu" not in reconstructed_device.meta
    assert reconstructed_device.meta["envs"] == {}
    assert reconstructed_device.meta["ports"] == {}
    assert reconstructed_device.meta["sysctls"] == {}
    assert len(lab.links) == 0


def test_get_lab_from_api_exception(kubernetes_manager):
    with pytest.raises(Exception):
        kubernetes_manager.get_lab_from_api()


#
# TESTS: update_lab_from_api
#
def test_update_lab_from_api_not_supported(kubernetes_manager):
    lab = Lab("test")

    with pytest.raises(NotSupportedError):
        kubernetes_manager.update_lab_from_api(lab)


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
def test_get_machines_stats_lab_obj(mock_get_machines_stats, kubernetes_manager, two_device_scenario):
    kubernetes_manager.get_machines_stats(lab=two_device_scenario)
    mock_get_machines_stats.assert_called_once_with(lab_hash=two_device_scenario.hash.lower(),
                                                    machine_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_stats")
def test_get_machines_stats_no_labs(mock_get_machines_stats, kubernetes_manager):
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
def test_get_machine_stats_lab_obj(mock_get_machines_stats, default_device, kubernetes_manager, two_device_scenario):
    mock_get_machines_stats.return_value = iter([{"test_device": KubernetesMachineStats(default_device.api_object)}])
    next(kubernetes_manager.get_machine_stats(machine_name="test_device", lab=two_device_scenario))
    mock_get_machines_stats.assert_called_once_with(lab_hash=two_device_scenario.hash.lower(),
                                                    machine_name="test_device")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesManager.KubernetesManager.get_machines_stats")
def test_get_machine_stats_invocation_error(mock_get_machines_stats, kubernetes_manager):
    mock_get_machines_stats.return_value = iter([])
    with pytest.raises(InvocationError):
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
def test_get_links_stats_lab_obj(mock_get_links_stats, kubernetes_manager, two_device_scenario):
    kubernetes_manager.get_links_stats(lab=two_device_scenario)
    mock_get_links_stats.assert_called_once_with(lab_hash=two_device_scenario.hash.lower(), link_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_links_stats_no_labs(mock_get_links_stats, kubernetes_manager):
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
def test_get_link_stats_lab_obj(mock_get_links_stats, kubernetes_network, kubernetes_manager, two_device_scenario):
    mock_get_links_stats.return_value = iter([{"test_network": KubernetesLinkStats(kubernetes_network)}])
    next(kubernetes_manager.get_links_stats(link_name="test_network", lab=two_device_scenario))
    mock_get_links_stats.assert_called_once_with(lab_hash=two_device_scenario.hash.lower(),
                                                 link_name="test_network")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesLink.KubernetesLink.get_links_stats")
def test_get_link_stats_invocation_error(mock_get_links_stats, kubernetes_manager):
    with pytest.raises(InvocationError):
        next(kubernetes_manager.get_link_stats(link_name="test_network"))
    assert not mock_get_links_stats.called
