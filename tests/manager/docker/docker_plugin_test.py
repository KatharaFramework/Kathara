import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from docker.errors import NotFound

from src.Kathara import utils

sys.path.insert(0, './')

from src.Kathara.manager.docker.DockerPlugin import DockerPlugin
from src.Kathara.exceptions import DockerPluginError


@pytest.fixture()
def mock_setting():
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': False,
        'remote_url': None,
        'network_plugin': 'kathara/katharanp'
    })

    return setting_mock


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("docker.DockerClient")
def docker_plugin_vde(mock_docker_client, mock_setting_get_instance, mock_setting):
    mock_setting.network_plugin = 'kathara/katharanp_vde'
    mock_setting_get_instance.return_value = mock_setting
    return DockerPlugin(mock_docker_client)


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("docker.DockerClient")
def docker_plugin_bridge(mock_docker_client, mock_setting_get_instance, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
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


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                               mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                               mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    docker_plugin_bridge.check_and_download_plugin()
    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_xtables_lock_mount.assert_called_once()
    mock_configure_xtables_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                           mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                           mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    mock_plugin.enabled = True
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    docker_plugin_bridge.check_and_download_plugin()
    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_xtables_lock_mount.assert_called_once()
    mock_plugin.disable.assert_called_once()
    mock_configure_xtables_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_not_found(mock_setting_get_instance, mock_xtables_lock_mount,
                                             docker_plugin_bridge, mock_plugin, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = None
    docker_plugin_bridge.client.plugins.get.side_effect = NotFound('Fail')
    docker_plugin_bridge.client.plugins.install.return_value = mock_plugin
    mock_plugin.enabled = False
    docker_plugin_bridge.check_and_download_plugin()
    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    assert not mock_plugin.upgrade.called
    mock_xtables_lock_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()
    assert not mock_plugin.disable.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_remote_plugin_not_installed(mock_setting_get_instance, mock_xtables_lock_mount,
                                                        mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                                        mock_setting):
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = None
    docker_plugin_bridge.client.plugins.get.side_effect = NotFound('Fail')
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_bridge.check_and_download_plugin()

    assert str(e.value) == "Kathara Network Plugin not found on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_remote_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                      mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                                      mock_setting):
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_bridge.check_and_download_plugin()

    assert str(e.value) == "Kathara Network Plugin not enabled on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_vde_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                   mock_configure_xtables_mount, docker_plugin_vde, mock_plugin,
                                                   mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = mock_plugin
    docker_plugin_vde.check_and_download_plugin()
    docker_plugin_vde.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_plugin.enable.assert_called_once()
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_vde_plugin_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                               mock_configure_xtables_mount, docker_plugin_vde, mock_plugin,
                                               mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting_get_instance.return_value = mock_setting
    mock_plugin.enabled = True
    docker_plugin_vde.client.plugins.get.return_value = mock_plugin
    docker_plugin_vde.check_and_download_plugin()
    docker_plugin_vde.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    assert not mock_plugin.enable.called
    assert not mock_xtables_lock_mount.called
    assert not mock_plugin.disable.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_vde_plugin_not_found(mock_setting_get_instance, mock_xtables_lock_mount,
                                                 docker_plugin_vde, mock_plugin, mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = None
    docker_plugin_vde.client.plugins.get.side_effect = NotFound('Fail')
    docker_plugin_vde.client.plugins.install.return_value = mock_plugin
    mock_plugin.enabled = False
    docker_plugin_vde.check_and_download_plugin()
    docker_plugin_vde.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:" + utils.get_architecture())
    assert not mock_plugin.upgrade.called
    mock_plugin.enable.assert_called_once()
    assert not mock_xtables_lock_mount.called
    assert not mock_plugin.disable.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_remote_vde_plugin_not_installed(mock_setting_get_instance, mock_xtables_lock_mount,
                                                            mock_configure_xtables_mount, docker_plugin_vde,
                                                            mock_plugin, mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = None
    docker_plugin_vde.client.plugins.get.side_effect = NotFound('Fail')
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_vde.check_and_download_plugin()

    assert str(e.value) == "Kathara Network Plugin not found on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_remote_vde_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                          mock_configure_xtables_mount, docker_plugin_vde,
                                                          mock_plugin, mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = mock_plugin
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_vde.check_and_download_plugin()

    assert str(e.value) == "Kathara Network Plugin not enabled on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


#
# TEST: plugin_store_path / plugin_host_store_path
#
def _plugin_with_settings(docker_plugin, settings):
    plugin = Mock()
    plugin.settings = settings
    docker_plugin.client.plugins.get.return_value = plugin


def test_plugin_store_paths(docker_plugin_vde):
    _plugin_with_settings(docker_plugin_vde, {'Mounts': [
        {'Name': 'var_run_docker', 'Source': '/var/run/docker', 'Destination': '/var/run/docker'},
        {'Name': 'tmp', 'Source': '/tmp', 'Destination': '/hosttmp'}
    ]})

    assert docker_plugin_vde.plugin_store_path() == "/hosttmp/katharanp"
    assert docker_plugin_vde.plugin_host_store_path() == "/tmp/katharanp"


def test_plugin_store_paths_no_mount_error(docker_plugin_vde):
    _plugin_with_settings(docker_plugin_vde, {'Mounts': []})

    with pytest.raises(FileNotFoundError):
        docker_plugin_vde.plugin_store_path()

    with pytest.raises(FileNotFoundError):
        docker_plugin_vde.plugin_host_store_path()


#
# TEST: supported_link_modes
#
@pytest.mark.parametrize("env,expected", [
    (["KATHARA_SWITCH_MODES=hub,switch,managed"], {"hub", "switch", "managed"}),
    (["OTHER=1", "KATHARA_SWITCH_MODES=hub, switch"], {"hub", "switch"}),
    (["OTHER=1"], {"hub"}),
    ([], {"hub"}),
    (None, {"hub"}),
])
def test_supported_link_modes(docker_plugin_vde, env, expected):
    _plugin_with_settings(docker_plugin_vde, {'Mounts': [], 'Env': env})

    assert docker_plugin_vde.supported_link_modes() == expected


def test_supported_link_modes_no_env(docker_plugin_vde):
    _plugin_with_settings(docker_plugin_vde, {'Mounts': []})

    assert docker_plugin_vde.supported_link_modes() == {"hub"}
