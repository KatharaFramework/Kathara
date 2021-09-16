import sys
from unittest import mock
from unittest.mock import Mock

import docker.types

import pytest

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.manager.docker.DockerLink import DockerLink
from src.Kathara import utils


@pytest.fixture()
def default_link():
    from src.Kathara.model.Link import Link
    return Link(Lab("default_scenario"), "A")


@pytest.fixture()
@mock.patch("docker.DockerClient")
def docker_link(mock_obj):
    return DockerLink(mock_obj)


@pytest.fixture()
@mock.patch("docker.models.networks.Network")
def docker_network(mock_network):
    return mock_network


@pytest.fixture()
@mock.patch("progressbar.ProgressBar")
def progress_bar(mock_progress_bar):
    return mock_progress_bar


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_network_name(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': False,
        'net_prefix': 'kathara'
    })
    mock_setting_get_instance.return_value = setting_mock
    link_name = DockerLink.get_network_name("A")
    assert link_name == "kathara_user_A"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_network_name_multiuser(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': True,
        'net_prefix': 'CUSTOM_PREFIX'
    })
    mock_setting_get_instance.return_value = setting_mock
    link_name = DockerLink.get_network_name("A")
    assert link_name == "CUSTOM_PREFIX_A"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create(mock_get_current_user_name, mock_setting_get_instance, docker_link, default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': False,
        'net_prefix': 'kathara',
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_user_A",
        driver="kathara/katharanp:latest",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "lab_hash": utils.generate_urlsafe_hash("default_scenario"),
            "name": "A",
            "user": "user",
            "app": "kathara",
            "external": ""
        }
    )


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_multiuser(mock_get_current_user_name, mock_setting_get_instance, docker_link, default_link):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': True,
        'net_prefix': 'kathara'
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_link.create(default_link)
    docker_link.client.networks.create.assert_called_once_with(
        name="kathara_A",
        driver="kathara/katharanp:latest",
        check_duplicate=True,
        ipam=docker.types.IPAMConfig(driver='null'),
        labels={
            "lab_hash": utils.generate_urlsafe_hash("default_scenario"),
            "name": "A",
            "user": "shared",
            "app": "kathara",
            "external": ""
        }
    )


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.create")
def test_deploy_link(mock_create, docker_link, progress_bar, default_link):
    docker_link._deploy_link(progress_bar, ("", default_link))
    mock_create.called_once_with(default_link)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links(mock_deploy_link, docker_link, progress_bar):
    lab = Lab("Default scenario")
    link_a = lab.get_or_new_link("A")
    link_b = lab.get_or_new_link("B")
    link_c = lab.get_or_new_link("C")
    docker_link.deploy_links(lab)
    mock_deploy_link.assert_any_call(None, ("A", link_a))
    mock_deploy_link.assert_any_call(None, ("B", link_b))
    mock_deploy_link.assert_any_call(None, ("C", link_c))
    assert mock_deploy_link.call_count == 3


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._deploy_link")
def test_deploy_links_no_link(mock_deploy_link, docker_link, progress_bar):
    lab = Lab("Default scenario")
    docker_link.deploy_links(lab)
    assert not mock_deploy_link.called


@mock.patch("docker.models.networks.Network")
def test_delete_link(docker_network):
    DockerLink._delete_link(docker_network)
    docker_network.remove.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
def test_undeploy_link(mock_undeploy_link, docker_link, docker_network, progress_bar):
    docker_link._undeploy_link(progress_bar, docker_network)
    mock_undeploy_link.called_once_with(docker_network)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters("lab_hash_value", "link_name_value", "user_name_value")
    filters = {"label": ["app=kathara", "lab_hash=lab_hash_value", "user=user_name_value"], "name": "link_name_value"}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_empty_filters(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters()
    filters = {"label": ["app=kathara"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_only_lab_hash(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters("lab_hash_value")
    filters = {"label": ["app=kathara", "lab_hash=lab_hash_value"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_only_link_name(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters(None, "link_name_value")
    filters = {"label": ["app=kathara"], "name": "link_name_value"}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.list")
def test_get_links_by_filters_only_user_name(mock_network_list, docker_link):
    docker_link.get_links_api_objects_by_filters(None, None, "user_name_value")
    filters = {"label": ["app=kathara", "user=user_name_value"]}
    mock_network_list.called_once_with(filters=filters)


@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_undeploy(mock_get_links_by_filters, mock_undeploy_link, mock_net1, mock_net2, mock_net3,
                  docker_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")
    mock_get_links_by_filters.return_value = [mock_net1, mock_net2, mock_net3]
    docker_link.undeploy("lab_hash")
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_net1.reload.call_count == 1
    assert mock_net2.reload.call_count == 1
    assert mock_net3.reload.call_count == 1
    assert mock_undeploy_link.call_count == 3


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_undeploy_empty_lab(mock_get_links_by_filters, mock_undeploy_link, docker_link):
    lab = Lab("Default scenario")
    mock_get_links_by_filters.return_value = []
    docker_link.undeploy("lab_hash")
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert not mock_undeploy_link.called


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink._undeploy_link")
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("docker.models.networks.Network")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_wipe(mock_get_links_by_filters, mock_net1, mock_net2, mock_net3, mock_undeploy_link, docker_link):
    lab = Lab("Default scenario")
    lab.get_or_new_link("A")
    lab.get_or_new_link("B")
    lab.get_or_new_link("C")
    mock_get_links_by_filters.return_value = [mock_net1, mock_net2, mock_net3]
    docker_link.wipe()
    mock_get_links_by_filters.called_once_with(lab.hash)
    assert mock_net1.reload.call_count == 1
    assert mock_net2.reload.call_count == 1
    assert mock_net3.reload.call_count == 1
    assert mock_undeploy_link.call_count == 3
