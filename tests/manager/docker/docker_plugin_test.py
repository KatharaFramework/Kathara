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
def test_check_from_list_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                            mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                            mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    docker_plugin_bridge.check_from_list({"kathara/katharanp:" + utils.get_architecture()})
    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_xtables_lock_mount.assert_called_once()
    mock_configure_xtables_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_plugin_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                        mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                        mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    mock_plugin.enabled = True
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    docker_plugin_bridge.check_from_list({"kathara/katharanp:" + utils.get_architecture()})
    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_xtables_lock_mount.assert_called_once()
    mock_plugin.disable.assert_called_once()
    mock_configure_xtables_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_plugin_not_found(mock_setting_get_instance, mock_xtables_lock_mount,
                                          docker_plugin_bridge, mock_plugin, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = None
    docker_plugin_bridge.client.plugins.get.side_effect = NotFound('Fail')
    docker_plugin_bridge.client.plugins.install.return_value = mock_plugin
    mock_plugin.enabled = False
    docker_plugin_bridge.check_from_list({"kathara/katharanp:" + utils.get_architecture()})
    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp:" + utils.get_architecture())
    assert not mock_plugin.upgrade.called
    mock_xtables_lock_mount.assert_called_once()
    mock_plugin.enable.assert_called_once()
    assert not mock_plugin.disable.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_remote_plugin_not_installed(mock_setting_get_instance, mock_xtables_lock_mount,
                                                     mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                                     mock_setting):
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = None
    docker_plugin_bridge.client.plugins.get.side_effect = NotFound('Fail')
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_bridge.check_from_list({"kathara/katharanp:" + utils.get_architecture()})

    assert str(
        e.value) == f"Kathara Network Plugin (kathara/katharanp:{utils.get_architecture()}) not found on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_remote_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                   mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                                   mock_setting):
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_bridge.check_from_list({"kathara/katharanp:" + utils.get_architecture()})

    assert str(
        e.value) == f"Kathara Network Plugin (kathara/katharanp:{utils.get_architecture()}) not enabled on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_vde_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                mock_configure_xtables_mount, docker_plugin_vde, mock_plugin,
                                                mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = mock_plugin
    docker_plugin_vde.check_from_list({"kathara/katharanp_vde:" + utils.get_architecture()})
    docker_plugin_vde.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    mock_plugin.enable.assert_called_once()
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_vde_plugin_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                            mock_configure_xtables_mount, docker_plugin_vde, mock_plugin,
                                            mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting_get_instance.return_value = mock_setting
    mock_plugin.enabled = True
    docker_plugin_vde.client.plugins.get.return_value = mock_plugin
    docker_plugin_vde.check_from_list({"kathara/katharanp_vde:" + utils.get_architecture()})
    docker_plugin_vde.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:" + utils.get_architecture())
    mock_plugin.upgrade.assert_called_once()
    assert not mock_plugin.enable.called
    assert not mock_xtables_lock_mount.called
    assert not mock_plugin.disable.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_vde_plugin_not_found(mock_setting_get_instance, mock_xtables_lock_mount,
                                              docker_plugin_vde, mock_plugin, mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = None
    docker_plugin_vde.client.plugins.get.side_effect = NotFound('Fail')
    docker_plugin_vde.client.plugins.install.return_value = mock_plugin
    mock_plugin.enabled = False
    docker_plugin_vde.check_from_list({"kathara/katharanp_vde:" + utils.get_architecture()})
    docker_plugin_vde.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:" + utils.get_architecture())
    assert not mock_plugin.upgrade.called
    mock_plugin.enable.assert_called_once()
    assert not mock_xtables_lock_mount.called
    assert not mock_plugin.disable.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_remote_vde_plugin_not_installed(mock_setting_get_instance, mock_xtables_lock_mount,
                                                         mock_configure_xtables_mount, docker_plugin_vde,
                                                         mock_plugin, mock_setting):
    plugin_name = "kathara/katharanp_vde"
    arch = utils.get_architecture()

    mock_setting.network_plugin = plugin_name
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = None
    docker_plugin_vde.client.plugins.get.side_effect = NotFound('Fail')
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_vde.check_from_list({plugin_name + ":" + arch})

    assert str(e.value) == f"Kathara Network Plugin ({plugin_name}:{arch}) not found on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_remote_vde_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                       mock_configure_xtables_mount, docker_plugin_vde,
                                                       mock_plugin, mock_setting):
    mock_setting.network_plugin = "kathara/katharanp_vde"
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_vde.client.plugins.get.return_value = mock_plugin
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_vde.check_from_list({"kathara/katharanp_vde:" + utils.get_architecture()})

    assert str(e.value) == \
           f"Kathara Network Plugin (kathara/katharanp_vde:{utils.get_architecture()}) not enabled on remote Docker connection."
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_plugin_from_link_type(mock_setting_get_instance, docker_plugin_bridge, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    # Like `current_name`, the driver name must be tagged with the architecture, otherwise Docker looks for `:latest`
    arch = utils.get_architecture()
    assert docker_plugin_bridge.get_plugin_from_link_type("bridge") == f"kathara/katharanp:{arch}"
    assert docker_plugin_bridge.get_plugin_from_link_type("hub") == f"kathara/katharanp_vde:{arch}"
    assert docker_plugin_bridge.get_plugin_from_link_type("p2p") == f"kathara/katharanp_p2p:{arch}"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_plugin_from_link_type_none_uses_current_plugin(mock_setting_get_instance, docker_plugin_bridge,
                                                            docker_plugin_vde, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    assert docker_plugin_bridge.get_plugin_from_link_type(None) == docker_plugin_bridge._default_name
    assert docker_plugin_vde.get_plugin_from_link_type(None) == docker_plugin_vde._default_name


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_plugin_from_link_type_unknown_type(mock_setting_get_instance, docker_plugin_bridge, mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    with pytest.raises(KeyError):
        docker_plugin_bridge.get_plugin_from_link_type("switch")


def test_check_from_list_checks_every_plugin(docker_plugin_bridge, mock_setting):
    with mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._check_and_download") as mock_check:
        docker_plugin_bridge.check_from_list({"plugin-a", "plugin-b"})

    assert mock_check.call_count == 2
    assert {c.args[-1] for c in mock_check.call_args_list} == {"plugin-a", "plugin-b"}


def test_check_from_list_empty(docker_plugin_bridge):
    with mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._check_and_download") as mock_check:
        docker_plugin_bridge.check_from_list(set())

    assert not mock_check.called


@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._configure_xtables_mount")
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin._xtables_lock_mount")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_p2p_plugin_not_enabled(mock_setting_get_instance, mock_xtables_lock_mount,
                                                mock_configure_xtables_mount, docker_plugin_bridge, mock_plugin,
                                                mock_setting):
    p2p_name = "kathara/katharanp_p2p:" + utils.get_architecture()
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    docker_plugin_bridge.check_from_list({p2p_name})
    docker_plugin_bridge.client.plugins.get.assert_called_once_with(p2p_name)
    mock_plugin.upgrade.assert_called_once()
    mock_plugin.enable.assert_called_once()
    # Only the Linux bridge plugin needs the xtables.lock mount
    assert not mock_xtables_lock_mount.called
    assert not mock_configure_xtables_mount.called


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_p2p_plugin_enabled(mock_setting_get_instance, docker_plugin_bridge, mock_plugin,
                                            mock_setting):
    mock_setting_get_instance.return_value = mock_setting
    mock_plugin.enabled = True
    docker_plugin_bridge.client.plugins.get.return_value = mock_plugin
    docker_plugin_bridge.check_from_list({"kathara/katharanp_p2p:" + utils.get_architecture()})
    mock_plugin.upgrade.assert_called_once()
    assert not mock_plugin.enable.called
    assert not mock_plugin.disable.called


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_p2p_plugin_not_found(mock_setting_get_instance, docker_plugin_bridge, mock_plugin,
                                              mock_setting):
    p2p_name = "kathara/katharanp_p2p:" + utils.get_architecture()
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.side_effect = NotFound('Fail')
    docker_plugin_bridge.client.plugins.install.return_value = mock_plugin
    mock_plugin.enabled = False
    docker_plugin_bridge.check_from_list({p2p_name})
    docker_plugin_bridge.client.plugins.install.assert_called_once_with(p2p_name)
    assert not mock_plugin.upgrade.called
    mock_plugin.enable.assert_called_once()


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_from_list_remote_error_names_the_missing_plugin(mock_setting_get_instance, docker_plugin_bridge,
                                                               mock_setting):
    p2p_name = "kathara/katharanp_p2p:" + utils.get_architecture()
    mock_setting.remote_url = "http://remote-url.kt"
    mock_setting_get_instance.return_value = mock_setting
    docker_plugin_bridge.client.plugins.get.side_effect = NotFound('Fail')
    with pytest.raises(DockerPluginError) as e:
        docker_plugin_bridge.check_from_list({p2p_name})

    assert p2p_name in str(e.value)


def test_exec_by_version_dispatches_by_plugin_name(docker_plugin_bridge):
    fun_vde, fun_bridge, fun_p2p = Mock(return_value="vde"), Mock(return_value="bridge"), Mock(return_value="p2p")
    arch = utils.get_architecture()

    assert docker_plugin_bridge.exec_by_version(f"kathara/katharanp_vde:{arch}", fun_vde, fun_bridge, fun_p2p) == "vde"
    assert docker_plugin_bridge.exec_by_version(f"kathara/katharanp_p2p:{arch}", fun_vde, fun_bridge, fun_p2p) == "p2p"
    assert docker_plugin_bridge.exec_by_version(f"kathara/katharanp:{arch}", fun_vde, fun_bridge, fun_p2p) == "bridge"

    # Each callback is invoked once, with the plugin name
    fun_vde.assert_called_once_with(f"kathara/katharanp_vde:{arch}")
    fun_p2p.assert_called_once_with(f"kathara/katharanp_p2p:{arch}")
    fun_bridge.assert_called_once_with(f"kathara/katharanp:{arch}")


def test_plugin_pid_uses_given_plugin(docker_plugin_bridge):
    plugin = Mock()
    plugin.id = "plugin-id"
    docker_plugin_bridge.client.plugins.get.return_value = plugin
    with (mock.patch("os.path.exists", return_value=True),
          mock.patch("builtins.open", mock.mock_open(read_data='{"init_process_pid": 4321}'))):
        assert docker_plugin_bridge.plugin_pid("kathara/katharanp_vde:amd64") == 4321

    docker_plugin_bridge.client.plugins.get.assert_called_once_with("kathara/katharanp_vde:amd64")


def test_exec_by_version_invalid_plugin_name(docker_plugin_bridge):
    fun_vde, fun_bridge, fun_p2p = Mock(), Mock(), Mock()

    # Names merely containing `vde` or `p2p` must not be dispatched to those callbacks
    for name in ["other/katharanp:amd64", "other/p2p_vde_like:amd64", "kathara/katharanp_vde_extra:amd64"]:
        with pytest.raises(DockerPluginError) as e:
            docker_plugin_bridge.exec_by_version(name, fun_vde, fun_bridge, fun_p2p)

        assert name in str(e.value)

    assert not fun_vde.called
    assert not fun_bridge.called
    assert not fun_p2p.called
