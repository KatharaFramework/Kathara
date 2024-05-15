import sys
from unittest import mock
from unittest.mock import Mock, call

import pytest
from kubernetes.client import V1PodList

sys.path.insert(0, './')

from kubernetes import client
from src.Kathara.exceptions import InvocationError
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.manager.kubernetes.KubernetesMachine import KubernetesMachine, STARTUP_COMMANDS


#
# FIXTURE
#
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
@mock.patch("kubernetes.client.models.v1_deployment.V1Deployment")
def default_device_b(mock_kubernetes_deployment):
    device = Machine(Lab("default_scenario"), "test_device_b")
    device.add_meta("exec", "ls")
    device.add_meta("mem", "64m")
    device.add_meta("cpus", "2")
    device.add_meta("image", "kathara/tes2")
    device.add_meta("bridged", False)
    device.add_meta('real_name', "devprefix-test-device-b-ec84ad3b")

    device.api_object = mock_kubernetes_deployment

    return device


@pytest.fixture()
@mock.patch("kubernetes.client.models.v1_deployment.V1Deployment")
def default_device_c(mock_kubernetes_deployment):
    device = Machine(Lab("default_scenario"), "test_device_c")
    device.add_meta("exec", "ls")
    device.add_meta("mem", "64m")
    device.add_meta("cpus", "2")
    device.add_meta("image", "kathara/test3")
    device.add_meta("bridged", False)
    device.add_meta('real_name', "devprefix-test-device-c-ec84ad3b")

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


@pytest.fixture()
def kubernetes_namespace():
    kubernetes_namespace_mock = Mock()
    metadata_mock = Mock()
    metadata_mock.configure_mock(**{
        'name': 'test_namespace',
    })
    kubernetes_namespace_mock.configure_mock(**{
        'metadata': metadata_mock
    })
    return kubernetes_namespace_mock


#
# TEST: get_deployment_name
#
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


#
# TEST: _build_definition
#
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


#
# TEST: create
#
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
                                                                          'net.ipv6.conf.all.accept_ra': 0,
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


#
# TEST: _deploy_machine
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.create")
def test_deploy_machine(mock_create, kubernetes_machine, default_device):
    machine_item = ("", default_device)

    mock_create.return_value = True

    kubernetes_machine._deploy_machine(machine_item)

    mock_create.assert_called_once()


#
# TEST: deploy_machines
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_startup")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._deploy_machine")
def test_deploy_machines(mock_deploy, mock_wait_machines_startup, mock_setting_get_instance, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "host_shared": False,
        "api_server_url": "",
        'api_token': ""
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")

    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})

    mock_deploy.return_value = None

    kubernetes_machine.deploy_machines(lab)

    assert mock_deploy.call_count == 2
    mock_deploy.assert_any_call(('pc1', pc1))
    mock_deploy.assert_any_call(('pc2', pc2))
    mock_wait_machines_startup.assert_called_once_with(lab, None)


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_startup")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._deploy_machine")
def test_deploy_machines_selected_machines(mock_deploy, mock_wait_machines_startup, mock_setting_get_instance,
                                           kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "host_shared": False,
        "api_server_url": "",
        'api_token': ""
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})

    mock_deploy.return_value = None
    kubernetes_machine.deploy_machines(lab, selected_machines={"pc1"})

    assert mock_deploy.call_count == 1
    mock_deploy.assert_any_call(('pc1', pc1))
    assert call(('pc2', pc2)) not in mock_deploy.mock_calls
    mock_wait_machines_startup.assert_called_once_with(lab, {"pc1"})


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_startup")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._deploy_machine")
def test_deploy_machines_excluded_machines(mock_deploy, mock_wait_machines_startup, mock_setting_get_instance,
                                           kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "host_shared": False,
        "api_server_url": "",
        'api_token': ""
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})

    mock_deploy.return_value = None

    kubernetes_machine.deploy_machines(lab, excluded_machines={"pc1"})

    assert mock_deploy.call_count == 1
    assert call(('pc1', pc1)) not in mock_deploy.mock_calls
    mock_deploy.assert_any_call(('pc2', pc2))
    mock_wait_machines_startup.assert_called_once_with(lab, {"pc2"})


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_startup")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._deploy_machine")
def test_deploy_machines_selected_and_excluded_machines(mock_deploy, mock_wait_machines_startup,
                                                        mock_setting_get_instance, kubernetes_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "host_shared": False,
        "api_server_url": "",
        'api_token': ""
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    with pytest.raises(InvocationError):
        kubernetes_machine.deploy_machines(lab, selected_machines={"pc1", "pc3"}, excluded_machines={"pc1"})
    assert not mock_deploy.called
    assert not mock_wait_machines_startup.called


#
# TEST: undeploy
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_shutdown")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_one_device(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                             mock_wait_machines_shutdown, kubernetes_machine, default_device):
    default_device.api_object.metadata.labels = {'name': "test_device"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    mock_undeploy_machine.return_value = None

    kubernetes_machine.undeploy("lab_hash", selected_machines={default_device.name})

    mock_get_machines_api_objects_by_filters.assert_called_once()
    mock_undeploy_machine.assert_called_once_with(default_device.api_object)
    mock_wait_machines_shutdown.assert_called_once_with("lab_hash", {default_device.name})


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_shutdown")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_three_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                                mock_wait_machines_shutdown, kubernetes_machine,
                                default_device, default_device_b, default_device_c):
    default_device.api_object.metadata.labels = {'name': "test_device"}
    default_device_b.api_object.metadata.labels = {'name': "test_device_b"}
    default_device_c.api_object.metadata.labels = {'name': "test_device_c"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device_b.api_object, default_device_c.api_object]
    mock_undeploy_machine.return_value = None

    kubernetes_machine.undeploy("lab_hash")

    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 3
    mock_undeploy_machine.assert_any_call(default_device.api_object)
    mock_undeploy_machine.assert_any_call(default_device_b.api_object)
    mock_undeploy_machine.assert_any_call(default_device_c.api_object)

    mock_wait_machines_shutdown.assert_called_once_with("lab_hash", {"test_device", "test_device_b", "test_device_c"})


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_shutdown")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_no_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                             mock_wait_machines_shutdown, kubernetes_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_undeploy_machine.return_value = None

    kubernetes_machine.undeploy("lab_hash")

    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert not mock_undeploy_machine.called
    assert not mock_wait_machines_shutdown.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_shutdown")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_selected_machines(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                                    mock_wait_machines_shutdown, kubernetes_machine,
                                    default_device, default_device_b, default_device_c):
    default_device.api_object.metadata.labels = {'name': "test_device"}
    default_device_b.api_object.metadata.labels = {'name': "test_device_b"}
    default_device_c.api_object.metadata.labels = {'name': "test_device_c"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device_b.api_object, default_device_c.api_object]
    mock_undeploy_machine.return_value = None
    kubernetes_machine.undeploy("lab_hash", selected_machines={"test_device"})
    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 1
    mock_undeploy_machine.assert_any_call(default_device.api_object)
    assert call(default_device_b.api_object) not in mock_undeploy_machine.mock_calls
    assert call(default_device_c.api_object) not in mock_undeploy_machine.mock_calls

    mock_wait_machines_shutdown.assert_called_once_with("lab_hash", {"test_device"})


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_shutdown")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_excluded_machines(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                                    mock_wait_machines_shutdown, kubernetes_machine,
                                    default_device, default_device_b, default_device_c):
    default_device.api_object.metadata.labels = {'name': "test_device"}
    default_device_b.api_object.metadata.labels = {'name': "test_device_b"}
    default_device_c.api_object.metadata.labels = {'name': "test_device_c"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device_b.api_object, default_device_c.api_object]
    mock_undeploy_machine.return_value = None
    kubernetes_machine.undeploy("lab_hash", excluded_machines={"test_device"})
    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 2
    assert call(default_device.api_object) not in mock_undeploy_machine.mock_calls
    mock_undeploy_machine.assert_any_call(default_device_b.api_object)
    mock_undeploy_machine.assert_any_call(default_device_c.api_object)

    mock_wait_machines_shutdown.assert_called_once_with("lab_hash", {"test_device_b", "test_device_c"})


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._wait_machines_shutdown")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_undeploy_selected_and_excluded_machines(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                                                 mock_wait_machines_shutdown, kubernetes_machine):
    mock_undeploy_machine.return_value = None
    with pytest.raises(InvocationError):
        kubernetes_machine.undeploy(
            "lab_hash", selected_machines={"test_device", "test_device_b"}, excluded_machines={"test_device"}
        )
    assert not mock_get_machines_api_objects_by_filters.called
    assert not mock_undeploy_machine.called
    assert not mock_wait_machines_shutdown.called


#
# TEST: wipe
#
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


#
# TEST: _undeploy_machine
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine._delete_machine")
def test_undeploy_machine(mock_delete_machine, kubernetes_machine, default_device):
    mock_delete_machine.return_value = None

    kubernetes_machine._undeploy_machine(default_device.api_object)

    mock_delete_machine.assert_called_once()


#
# TEST: get_machines_api_objects_by_filter
#
@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api.list_namespaced_pod")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace.KubernetesNamespace.get_all")
def test_get_machines_api_objects_by_filter_empty_filter(mock_namespace_get_all, mock_list_namespaced_pod,
                                                         kubernetes_namespace, default_device, kubernetes_machine):
    mock_namespace_get_all.return_value = [kubernetes_namespace]
    kubernetes_machine.kubernetes_namespace.get_all = mock_namespace_get_all
    mock_list_namespaced_pod.return_value = V1PodList(items=[default_device])
    kubernetes_machine.core_client.list_namespaced_pod = mock_list_namespaced_pod
    kubernetes_machine.get_machines_api_objects_by_filters()
    mock_namespace_get_all.assert_called_once()
    mock_list_namespaced_pod.assert_called_once_with(namespace="test_namespace",
                                                     label_selector="app=kathara",
                                                     timeout_seconds=9999)


@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api.list_namespaced_pod")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace.KubernetesNamespace.get_all")
def test_get_machines_api_objects_by_filter_machine_name(mock_namespace_get_all, mock_list_namespaced_pod,
                                                         kubernetes_namespace, default_device, kubernetes_machine):
    mock_namespace_get_all.return_value = [kubernetes_namespace]
    kubernetes_machine.kubernetes_namespace.get_all = mock_namespace_get_all
    default_device.api_object.name = "test_device"
    mock_list_namespaced_pod.return_value = V1PodList(items=[default_device.api_object])
    kubernetes_machine.core_client.list_namespaced_pod = mock_list_namespaced_pod
    kubernetes_machine.get_machines_api_objects_by_filters(machine_name="test_device")
    mock_namespace_get_all.assert_called_once()
    mock_list_namespaced_pod.assert_called_once_with(namespace="test_namespace",
                                                     label_selector="app=kathara,name=test_device",
                                                     timeout_seconds=9999)


@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api.list_namespaced_pod")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace.KubernetesNamespace.get_all")
def test_get_machines_api_objects_by_filter_lab_hash(mock_namespace_get_all, mock_list_namespaced_pod,
                                                     kubernetes_namespace, default_device, kubernetes_machine):
    mock_list_namespaced_pod.return_value = V1PodList(items=[default_device.api_object])
    kubernetes_machine.core_client.list_namespaced_pod = mock_list_namespaced_pod
    kubernetes_machine.get_machines_api_objects_by_filters(lab_hash="lab_hash")
    assert not mock_namespace_get_all.called
    mock_list_namespaced_pod.assert_called_once_with(namespace="lab_hash",
                                                     label_selector="app=kathara",
                                                     timeout_seconds=9999)


@mock.patch("kubernetes.client.api.core_v1_api.CoreV1Api.list_namespaced_pod")
@mock.patch("src.Kathara.manager.kubernetes.KubernetesNamespace.KubernetesNamespace.get_all")
def test_get_machines_api_objects_by_filter_lab_hash_machine_name(mock_namespace_get_all, mock_list_namespaced_pod,
                                                                  kubernetes_namespace, default_device,
                                                                  kubernetes_machine):
    default_device.api_object.name = "test_device"
    mock_list_namespaced_pod.return_value = V1PodList(items=[default_device.api_object])
    kubernetes_machine.core_client.list_namespaced_pod = mock_list_namespaced_pod
    kubernetes_machine.get_machines_api_objects_by_filters(lab_hash="lab_hash", machine_name="test_device")
    assert not mock_namespace_get_all.called
    mock_list_namespaced_pod.assert_called_once_with(namespace="lab_hash",
                                                     label_selector="app=kathara,name=test_device",
                                                     timeout_seconds=9999)


#
# TEST: get_machines_stats
#
@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash(mock_get_machines_api_objects_by_filters, kubernetes_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    next(kubernetes_machine.get_machines_stats(lab_hash="lab_hash"))
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash",
                                                                     machine_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_device_name(mock_get_machines_api_objects_by_filters, kubernetes_machine,
                                                 default_device):
    default_device.api_object.name = "test_device"
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    next(kubernetes_machine.get_machines_stats(lab_hash="lab_hash", machine_name="test_device"))
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash",
                                                                     machine_name="test_device")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_no_hash_no_name(mock_get_machines_api_objects_by_filters, kubernetes_machine,
                                            default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    next(kubernetes_machine.get_machines_stats())
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash=None,
                                                                     machine_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_device_not_found(mock_get_machines_api_objects_by_filters, kubernetes_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    assert next(kubernetes_machine.get_machines_stats(lab_hash="lab_hash")) == {}
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash",
                                                                     machine_name=None)


@mock.patch("src.Kathara.manager.kubernetes.KubernetesMachine.KubernetesMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_device_not_found(mock_get_machines_api_objects_by_filters, kubernetes_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    assert next(kubernetes_machine.get_machines_stats()) == {}
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash=None,
                                                                     machine_name=None)
