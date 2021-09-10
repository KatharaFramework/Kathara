import sys
from unittest import mock
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
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def default_setting(mock_setting):
    return mock_setting


@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_network_name(mock_get_current_user_name, default_setting):
    mock_get_current_user_name.return_value = 'user'
    default_setting.return_value.multiuser = False
    default_setting.return_value.net_prefix = 'kathara'
    link_name = DockerLink.get_network_name("A")
    assert link_name == "kathara_user_A"


@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create(mock_get_current_user_name, docker_link, default_link, default_setting):
    docker_link.client.networks.list.return_value = []

    mock_get_current_user_name.return_value = 'user'
    default_setting.return_value.multiuser = False
    default_setting.return_value.net_prefix = 'kathara'
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
