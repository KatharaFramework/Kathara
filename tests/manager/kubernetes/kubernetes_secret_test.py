import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from kubernetes import client
from kubernetes.client import ApiException

sys.path.insert(0, './')

from src.Kathara.manager.kubernetes.KubernetesSecret import KubernetesSecret
from src.Kathara.model.Lab import Lab


@pytest.fixture()
def kubernetes_secret():
    secret = KubernetesSecret()
    secret.client = Mock()
    return secret


@pytest.fixture()
def default_scenario():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc1.name, "B")
    return lab


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_create_no_docker_config(mock_setting_get_instance, kubernetes_secret, default_scenario):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'docker_config_json': None
    })
    mock_setting_get_instance.return_value = setting_mock

    result = kubernetes_secret.create(default_scenario)

    assert len(result) == 0
    assert not kubernetes_secret.client.create_namespaced_secret.called


@mock.patch("src.Kathara.manager.kubernetes.KubernetesSecret.KubernetesSecret._create_secret")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_create_with_docker_config(mock_setting_get_instance, mock_create_secret, kubernetes_secret, default_scenario):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'docker_config_json': "config123"
    })
    mock_setting_get_instance.return_value = setting_mock

    expected_secret = client.V1Secret(
        metadata=client.V1ObjectMeta(
            name="private-registry", namespace="9pe3y6IDMwx4PfOPu5mbNg", labels={'app': 'kathara'}
        ),
        type="kubernetes.io/dockerconfigjson", data={".dockerconfigjson": "config123"}
    )
    mock_create_secret.return_value = expected_secret

    result = kubernetes_secret.create(default_scenario)

    assert len(result) == 1
    assert result[0] == expected_secret
    mock_create_secret.assert_called_once_with(
        "9pe3y6IDMwx4PfOPu5mbNg", "private-registry",
        "kubernetes.io/dockerconfigjson", {".dockerconfigjson": "config123"}
    )


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_create_exception(mock_setting_get_instance, kubernetes_secret, default_scenario):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'manager': 'kubernetes',
        'docker_config_json': "config123"
    })
    mock_setting_get_instance.return_value = setting_mock

    kubernetes_secret.client.create_namespaced_secret.side_effect = ApiException()

    result = kubernetes_secret.create(default_scenario)

    assert len(result) == 0


@mock.patch("src.Kathara.manager.kubernetes.KubernetesSecret.KubernetesSecret._wait_secret_creation")
def test_create_secret(mock_wait_secret_creation, kubernetes_secret, default_scenario):
    expected_secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name="private-registry", namespace="hash", labels={'app': 'kathara'}),
        type="kubernetes.io/dockerconfigjson", data={".dockerconfigjson": "config123"}
    )

    actual_secret = kubernetes_secret._create_secret(
        "hash", "private-registry",
        "kubernetes.io/dockerconfigjson", {".dockerconfigjson": "config123"}
    )

    assert actual_secret == expected_secret
    kubernetes_secret.client.create_namespaced_secret.assert_called_once_with(
        "hash", expected_secret
    )
    mock_wait_secret_creation.assert_called_once_with("hash", "private-registry")


@mock.patch("src.Kathara.manager.kubernetes.KubernetesSecret.KubernetesSecret._wait_secret_creation")
def test_create_secret_exception(mock_wait_secret_creation, kubernetes_secret, default_scenario):
    expected_secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name="private-registry", namespace="hash", labels={'app': 'kathara'}),
        type="kubernetes.io/dockerconfigjson", data={".dockerconfigjson": "config123"}
    )

    kubernetes_secret.client.create_namespaced_secret.side_effect = ApiException()

    actual_secret = kubernetes_secret._create_secret(
        "hash", "private-registry",
        "kubernetes.io/dockerconfigjson", {".dockerconfigjson": "config123"}
    )

    assert actual_secret is None
    kubernetes_secret.client.create_namespaced_secret.assert_called_once_with(
        "hash", expected_secret
    )
    assert not mock_wait_secret_creation.called
