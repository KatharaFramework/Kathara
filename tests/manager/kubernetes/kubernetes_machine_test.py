import sys
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from kubernetes import client
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.manager.kubernetes.KubernetesMachine import KubernetesMachine, STARTUP_COMMANDS


@pytest.fixture()
@mock.patch("kubernetes.client.api.apps_v1_api.AppsV1Api")
@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesConfigMap")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace")
def kubernetes_machine(kubernetes_namespace_mock, config_map_mock, core_v1_api_mock, apps_v1_api_mock):
    return KubernetesMachine(kubernetes_namespace_mock)


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
def kubernetes_device_definition():
    security_context = client.V1SecurityContext(privileged=True)
    resources = client.V1ResourceRequirements(limits={
        "memory": "64M",
        "cpu": "2000m"
    })

    sysctl_commands = "sysctl -w -q net.ipv4.conf.all.rp_filter=0; sysctl -w -q net.ipv4.conf.default.rp_filter=0; " \
                      "sysctl -w -q net.ipv4.conf.lo.rp_filter=0; sysctl -w -q net.ipv4.ip_forward=1; " \
                      "sysctl -w -q net.ipv4.icmp_ratelimit=0"
    startup_commands_string = "; ".join(STARTUP_COMMANDS) \
        .format(machine_name="test_device", sysctl_commands=sysctl_commands, machine_commands="ls")

    post_start = client.V1LifecycleHandler(
        _exec=client.V1ExecAction(
            command=["/bin/bash", "-c", startup_commands_string]
        )
    )
    container_definition = client.V1Container(
        name="devprefix-test-device-ec84ad3b",
        image="kathara/test",
        lifecycle=client.V1Lifecycle(post_start=post_start),
        stdin=True,
        tty=True,
        image_pull_policy="Always",
        ports=None,
        resources=resources,
        volume_mounts=[],
        security_context=security_context,
        env=[client.V1EnvVar("_MEGALOS_SHELL", "/bin/bash")]
    )

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": "[]"},
                                       labels={"name": "test_device", "app": "kathara"}
                                       )
    pod_spec = client.V1PodSpec(containers=[container_definition],
                                hostname="devprefix-test-device-ec84ad3b",
                                dns_policy="None",
                                dns_config=client.V1PodDNSConfig(nameservers=["127.0.0.1"]),
                                volumes=[]
                                )

    pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)
    label_selector = client.V1LabelSelector(match_labels={"name": "test_device", "app": "kathara"})
    deployment_spec = client.V1DeploymentSpec(replicas=1, template=pod_template, selector=label_selector)

    return client.V1Deployment(api_version="apps/v1",
                               kind="Deployment",
                               metadata=client.V1ObjectMeta(
                                   name="devprefix-test-device-ec84ad3b",
                                   labels={"name": "test_device", "app": "kathara"}
                               ),
                               spec=deployment_spec
                               )


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_deployment_name(mock_setting_get_instance, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'device_prefix': 'devprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    device_name = kubernetes_machine.get_deployment_name("device")
    assert device_name == "devprefix-device"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_deployment_name_with_underscore(mock_setting_get_instance, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'device_prefix': 'dev_prefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    k8s_device_name = kubernetes_machine.get_deployment_name("device_name")

    assert k8s_device_name == "devprefix-device-name-3b92d741"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_deployment_name_remove_invalid_chars(mock_setting_get_instance, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'device_prefix': 'devprefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    k8s_device_name = kubernetes_machine.get_deployment_name("Device05#A")

    assert k8s_device_name == "devprefix-device05a"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_build_definition_no_config(mock_setting_get_instance, default_device, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'devprefix',
        'device_shell': '/bin/bash',
        'enable_ipv6': False,
        'image_pull_policy': 'Always',
        'host_shared': False
    })
    mock_setting_get_instance.return_value = setting_mock

    security_context = client.V1SecurityContext(privileged=True)
    resources = client.V1ResourceRequirements(limits={
        "memory": "64M",
        "cpu": "2000m"
    })

    startup_commands_string = "; ".join(STARTUP_COMMANDS) \
        .format(machine_name="test_device", sysctl_commands="", machine_commands="ls")

    post_start = client.V1LifecycleHandler(
        _exec=client.V1ExecAction(
            command=["/bin/bash", "-c", startup_commands_string]
        )
    )
    container_definition = client.V1Container(
        name="devprefix-test-device-ec84ad3b",
        image="kathara/test",
        lifecycle=client.V1Lifecycle(post_start=post_start),
        stdin=True,
        tty=True,
        image_pull_policy="Always",
        ports=None,
        resources=resources,
        volume_mounts=[],
        security_context=security_context,
        env=[client.V1EnvVar("_MEGALOS_SHELL", "/bin/bash")]
    )

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": "[]"},
                                       labels={"name": "test_device", "app": "kathara"}
                                       )
    pod_spec = client.V1PodSpec(containers=[container_definition],
                                hostname="devprefix-test-device-ec84ad3b",
                                dns_policy="None",
                                dns_config=client.V1PodDNSConfig(nameservers=["127.0.0.1"]),
                                volumes=[]
                                )

    pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)
    label_selector = client.V1LabelSelector(match_labels={"name": "test_device", "app": "kathara"})
    deployment_spec = client.V1DeploymentSpec(replicas=1, template=pod_template, selector=label_selector)

    expected_definition = client.V1Deployment(api_version="apps/v1",
                                              kind="Deployment",
                                              metadata=client.V1ObjectMeta(
                                                  name="devprefix-test-device-ec84ad3b",
                                                  labels={"name": "test_device", "app": "kathara"}
                                              ),
                                              spec=deployment_spec
                                              )

    actual_definition = kubernetes_machine._build_definition(default_device, None)

    assert actual_definition == expected_definition


@mock.patch("kubernetes.client.models.v1_config_map.V1ConfigMap")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_build_definition(mock_setting_get_instance, config_map_mock, default_device, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'devprefix',
        'device_shell': '/bin/bash',
        'enable_ipv6': False,
        'image_pull_policy': 'Always',
        'host_shared': False
    })
    mock_setting_get_instance.return_value = setting_mock

    config_map_mock.metadata.name = "test_device_config_map"

    security_context = client.V1SecurityContext(privileged=True)
    resources = client.V1ResourceRequirements(limits={
        "memory": "64M",
        "cpu": "2000m"
    })

    startup_commands_string = "; ".join(STARTUP_COMMANDS) \
        .format(machine_name="test_device", sysctl_commands="", machine_commands="ls")

    post_start = client.V1LifecycleHandler(
        _exec=client.V1ExecAction(
            command=["/bin/bash", "-c", startup_commands_string]
        )
    )
    container_definition = client.V1Container(
        name="devprefix-test-device-ec84ad3b",
        image="kathara/test",
        lifecycle=client.V1Lifecycle(post_start=post_start),
        stdin=True,
        tty=True,
        image_pull_policy="Always",
        ports=None,
        resources=resources,
        volume_mounts=[client.V1VolumeMount(name="hostlab", mount_path="/tmp/kathara")],
        security_context=security_context,
        env=[client.V1EnvVar("_MEGALOS_SHELL", "/bin/bash")]
    )

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": "[]"},
                                       labels={"name": "test_device", "app": "kathara"}
                                       )
    pod_spec = client.V1PodSpec(containers=[container_definition],
                                hostname="devprefix-test-device-ec84ad3b",
                                dns_policy="None",
                                dns_config=client.V1PodDNSConfig(nameservers=["127.0.0.1"]),
                                volumes=[client.V1Volume(
                                    name="hostlab",
                                    config_map=client.V1ConfigMapVolumeSource(name="test_device_config_map")
                                )]
                                )

    pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)
    label_selector = client.V1LabelSelector(match_labels={"name": "test_device", "app": "kathara"})
    deployment_spec = client.V1DeploymentSpec(replicas=1, template=pod_template, selector=label_selector)

    expected_definition = client.V1Deployment(api_version="apps/v1",
                                              kind="Deployment",
                                              metadata=client.V1ObjectMeta(
                                                  name="devprefix-test-device-ec84ad3b",
                                                  labels={"name": "test_device", "app": "kathara"}
                                              ),
                                              spec=deployment_spec
                                              )

    actual_definition = kubernetes_machine._build_definition(default_device, config_map_mock)

    assert actual_definition == expected_definition


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_create(mock_setting_get_instance, kubernetes_machine, default_device, kubernetes_device_definition):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'devprefix',
        'device_shell': '/bin/bash',
        'enable_ipv6': False,
        'image_pull_policy': 'Always',
        'host_shared': False
    })
    mock_setting_get_instance.return_value = setting_mock

    kubernetes_machine.create(default_device)

    kubernetes_machine.client.create_namespaced_deployment.assert_called_once_with(
        body=kubernetes_device_definition,
        namespace="FwFaxbiuhvSWb2KpN5zw"
    )


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_create_ipv6(mock_setting_get_instance, kubernetes_machine, default_device):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'devprefix',
        'device_shell': '/bin/bash',
        'enable_ipv6': True,
        'image_pull_policy': 'Always',
        'host_shared': False
    })
    mock_setting_get_instance.return_value = setting_mock

    security_context = client.V1SecurityContext(privileged=True)
    resources = client.V1ResourceRequirements(limits={
        "memory": "64M",
        "cpu": "2000m"
    })

    sysctl_commands = "; ".join(["sysctl -w -q %s=%d" % item for item in {'net.ipv4.conf.all.rp_filter': 0,
                                                                          'net.ipv4.conf.default.rp_filter': 0,
                                                                          'net.ipv4.conf.lo.rp_filter': 0,
                                                                          'net.ipv4.ip_forward': 1,
                                                                          'net.ipv4.icmp_ratelimit': 0,
                                                                          'net.ipv6.conf.all.forwarding': 1,
                                                                          'net.ipv6.icmp.ratelimit': 0,
                                                                          'net.ipv6.conf.default.disable_ipv6': 0,
                                                                          'net.ipv6.conf.all.disable_ipv6': 0
                                                                          }.items()])
    startup_commands_string = "; ".join(STARTUP_COMMANDS) \
        .format(machine_name="test_device", sysctl_commands=sysctl_commands, machine_commands="ls")

    post_start = client.V1LifecycleHandler(
        _exec=client.V1ExecAction(
            command=["/bin/bash", "-c", startup_commands_string]
        )
    )
    container_definition = client.V1Container(
        name="devprefix-test-device-ec84ad3b",
        image="kathara/test",
        lifecycle=client.V1Lifecycle(post_start=post_start),
        stdin=True,
        tty=True,
        image_pull_policy="Always",
        ports=None,
        resources=resources,
        volume_mounts=[],
        security_context=security_context,
        env=[client.V1EnvVar("_MEGALOS_SHELL", "/bin/bash")]
    )

    pod_metadata = client.V1ObjectMeta(deletion_grace_period_seconds=0,
                                       annotations={"k8s.v1.cni.cncf.io/networks": "[]"},
                                       labels={"name": "test_device", "app": "kathara"}
                                       )
    pod_spec = client.V1PodSpec(containers=[container_definition],
                                hostname="devprefix-test-device-ec84ad3b",
                                dns_policy="None",
                                dns_config=client.V1PodDNSConfig(nameservers=["127.0.0.1"]),
                                volumes=[]
                                )

    pod_template = client.V1PodTemplateSpec(metadata=pod_metadata, spec=pod_spec)
    label_selector = client.V1LabelSelector(match_labels={"name": "test_device", "app": "kathara"})
    deployment_spec = client.V1DeploymentSpec(replicas=1, template=pod_template, selector=label_selector)

    expected_definition = client.V1Deployment(api_version="apps/v1",
                                              kind="Deployment",
                                              metadata=client.V1ObjectMeta(
                                                  name="devprefix-test-device-ec84ad3b",
                                                  labels={"name": "test_device", "app": "kathara"}
                                              ),
                                              spec=deployment_spec
                                              )

    kubernetes_machine.create(default_device)

    kubernetes_machine.client.create_namespaced_deployment.assert_called_once_with(
        body=expected_definition,
        namespace="FwFaxbiuhvSWb2KpN5zw"
    )


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.create")
def test_deploy_machine(mock_create, kubernetes_machine, default_device):
    machine_item = ("", default_device)

    mock_create.return_value = True

    kubernetes_machine._deploy_machine(machine_item)

    mock_create.assert_called_once()


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._deploy_machine")
def test_deploy_machines(mock_deploy, kubernetes_machine):
    lab = Lab("Default scenario")

    lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})

    mock_deploy.return_value = None

    kubernetes_machine.deploy_machines(lab)

    assert mock_deploy.call_count == 2


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_one_device(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, kubernetes_machine,
                             default_device):
    default_device.api_object.metadata.labels = {'name': "test_device"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    mock_undeploy_machine.return_value = None

    kubernetes_machine.undeploy("lab_hash", selected_machines={default_device.name})

    mock_get_machines_api_objects_by_filters.assert_called_once()
    mock_undeploy_machine.assert_called_once_with(default_device.api_object)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_three_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, kubernetes_machine,
                                default_device):
    default_device.api_object.metadata.labels = {'name': "test_device"}
    # fill the list with more devices
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device.api_object, default_device.api_object]
    mock_undeploy_machine.return_value = None

    kubernetes_machine.undeploy("lab_hash")

    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 3


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_no_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, kubernetes_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_undeploy_machine.return_value = None

    kubernetes_machine.undeploy("lab_hash")

    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert not mock_undeploy_machine.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_wipe_one_device(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, kubernetes_machine,
                         default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    mock_undeploy_machine.return_value = None

    kubernetes_machine.wipe()

    mock_undeploy_machine.assert_called_once()


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_wipe_no_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, kubernetes_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_undeploy_machine.return_value = None

    kubernetes_machine.wipe()

    assert not mock_undeploy_machine.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_wipe_three_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, kubernetes_machine,
                            default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object, default_device.api_object,
                                                             default_device.api_object]
    mock_undeploy_machine.return_value = None

    kubernetes_machine.wipe()

    assert mock_undeploy_machine.call_count == 3


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._delete_machine")
def test_undeploy_machine(mock_delete_machine, kubernetes_machine, default_device):
    mock_delete_machine.return_value = None

    kubernetes_machine._undeploy_machine(default_device.api_object)

    mock_delete_machine.assert_called_once()
