import sys
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.podman.PodmanLink import PodmanLink
from src.Kathara.model.ExternalLink import ExternalLink
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import NotSupportedError
from src.Kathara.types import SharedCollisionDomainsOption


@pytest.fixture()
@mock.patch("podman.PodmanClient")
def podman_link(mock_podman_client):
    return PodmanLink(mock_podman_client)


@pytest.fixture()
def default_lab():
    return Lab("Default scenario")


def _setting_mock(**overrides):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'net_prefix': 'net_prefix',
        'network_plugin': 'katharanp_vde',
        **overrides
    })
    return setting_mock


@mock.patch("src.Kathara.manager.podman.PodmanLink.PodmanLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_new_network(mock_get_current_user_name, mock_setting_get_instance, mock_get_links,
                            podman_link, default_lab):
    mock_get_links.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock()

    link = default_lab.get_or_new_link("A")
    podman_link.create(link)

    _, kwargs = podman_link.client.networks.create.call_args
    # The L2 topology (bridge, veths, interface names, MACs, per-interface sysctls) is owned by the
    # Kathará netavark plugin, not by Podman itself.
    assert kwargs['driver'] == 'katharanp_vde'
    # Podman only forwards the configuration: IPAM and DNS are disabled since Kathará assigns
    # addresses itself and machines do not need aardvark-dns.
    assert kwargs['dns_enabled'] is False
    assert 'internal' not in kwargs
    assert kwargs['labels']['name'] == 'A'
    assert kwargs['labels']['app'] == 'kathara'
    assert kwargs['labels']['user'] == 'test-user'
    assert kwargs['labels']['lab_hash'] == default_lab.hash
    # host-local IPAM is cosmetic for Kathara (interface IPs are always assigned manually):
    # opt out of it natively instead of leaving Podman's default active.
    assert kwargs['ipam']['Driver'] == 'none'

    assert link.api_object == podman_link.client.networks.create.return_value


@mock.patch("src.Kathara.manager.podman.PodmanLink.PodmanLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_new_network_linux_bridge_plugin(mock_get_current_user_name, mock_setting_get_instance,
                                                mock_get_links, podman_link, default_lab):
    mock_get_links.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock(network_plugin='katharanp')

    podman_link.create(default_lab.get_or_new_link("A"))

    _, kwargs = podman_link.client.networks.create.call_args
    assert kwargs['driver'] == 'katharanp'


@mock.patch("src.Kathara.manager.podman.PodmanLink.PodmanLink.get_links_api_objects_by_filters")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_idempotent(mock_get_current_user_name, mock_setting_get_instance, mock_get_links,
                           podman_link, default_lab):
    existing_network = Mock()
    mock_get_links.return_value = [existing_network]
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock()

    link = default_lab.get_or_new_link("A")
    podman_link.create(link)

    assert link.api_object == existing_network
    assert not podman_link.client.networks.create.called


@mock.patch("src.Kathara.manager.podman.PodmanLink.PodmanLink._deploy_link")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_deploy_links_external_not_supported(mock_setting_get_instance, mock_deploy_link, podman_link, default_lab):
    mock_setting_get_instance.return_value = _setting_mock()

    link = default_lab.get_or_new_link("A")
    link.external.append(ExternalLink("eth0"))

    with pytest.raises(NotSupportedError, match="External collision domains"):
        podman_link.deploy_links(default_lab)

    assert not mock_deploy_link.called
    assert not podman_link.client.networks.create.called


@mock.patch("src.Kathara.manager.podman.PodmanLink.PodmanLink._deploy_link")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_deploy_links_shared_between_users_not_supported(mock_setting_get_instance, mock_deploy_link, podman_link,
                                                          default_lab):
    mock_setting_get_instance.return_value = _setting_mock(shared_cds=SharedCollisionDomainsOption.USERS)

    default_lab.get_or_new_link("A")

    with pytest.raises(NotSupportedError, match="Collision domains shared between users"):
        podman_link.deploy_links(default_lab)

    assert not mock_deploy_link.called
    assert not podman_link.client.networks.create.called
