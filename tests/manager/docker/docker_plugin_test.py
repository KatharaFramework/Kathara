import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from docker.errors import NotFound

from src.Kathara import utils

sys.path.insert(0, './')

from src.Kathara.manager.docker.DockerPlugin import DockerPlugin


@pytest.fixture()
@mock.patch("docker.DockerClient")
def docker_plugin(mock_docker_client):
    return DockerPlugin(mock_docker_client)


@pytest.fixture()
def mock_plugin():
    mock_plugin = Mock()
    mock_plugin.configure_mock(**{
        'attrs': {
            'Settings': {
                'Mounts': [{'Description': '', 'Destination': '/mount/path', 'Name': 'xtables_lock',
                            'Options': ['rbind'], 'Settable': None, 'Source': '/mount/path', 'Type': 'bind'}]
            }
        },
        'enabled': False
    })
    return mock_plugin


@pytest.fixture()
def mock_setting():
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': False,
        'remote_url': None
    })

    return setting_mock


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._get_xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_not_enabled(mock_setting_get_instance, mock_get_xtables_lock_mount,
                                               mock_configure_xtables_mount, docker_plugin, mock_plugin, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin.client.plugins.get.return_value = mock_plugin
    docker_plugin.check_and_download_plugin()
    docker_plugin.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_get_xtables_lock_mount.assert_called_once()
    mock_configure_xtables_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._get_xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_enabled(mock_setting_get_instance, mock_get_xtables_lock_mount,
                                           mock_configure_xtables_mount, docker_plugin, mock_plugin, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    mock_plugin.enabled = True
    docker_plugin.client.plugins.get.return_value = mock_plugin
    docker_plugin.check_and_download_plugin()
    docker_plugin.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_get_xtables_lock_mount.assert_called_once()
    mock_plugin.disable.assert_called_once()
    mock_configure_xtables_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._get_xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_not_found(mock_setting_get_instance, mock_get_xtables_lock_mount,
                                             docker_plugin, mock_plugin, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin.client.plugins.get.return_value = None
    docker_plugin.client.plugins.get.side_effect = NotFound('Fail')
    docker_plugin.client.plugins.install.return_value = mock_plugin
    mock_plugin.enabled = False
    docker_plugin.check_and_download_plugin()
    docker_plugin.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    assert not mock_plugin.upgrade.called
    mock_get_xtables_lock_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()
    assert not mock_plugin.disable.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._get_xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_remote_plugin_not_installed(mock_setting_get_instance, mock_get_xtables_lock_mount,
                                                        mock_configure_xtables_mount, docker_plugin, mock_plugin,
                                                        mock_setting):
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin.client.plugins.get.return_value = None
    docker_plugin.client.plugins.get.side_effect = NotFound('Fail')
    with pytest.raises(Exception) as e:
        docker_plugin.check_and_download_plugin()

    assert str(e.value) == "Kathara Network Plugin not found on remote Docker connection."
    assert not mock_get_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._get_xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_remote_plugin_not_enabled(mock_setting_get_instance, mock_get_xtables_lock_mount,
                                                      mock_configure_xtables_mount, docker_plugin, mock_plugin,
                                                      mock_setting):
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin.client.plugins.get.return_value = mock_plugin
    with pytest.raises(Exception) as e:
        docker_plugin.check_and_download_plugin()

    assert str(e.value) == "Kathara Network Plugin not enabled on remote Docker connection."
    assert not mock_get_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called
