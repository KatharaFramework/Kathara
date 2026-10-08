import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.exceptions import PodmanPluginError
from src.Kathara.manager.podman.PodmanPlugin import PodmanPlugin


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_and_install")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_rejects_native_windows(mock_setting_get_instance, mock_download_and_install):
    mock_setting_get_instance.return_value.api_socket_url = None
    with mock.patch.object(sys, "platform", "win32"):
        with pytest.raises(PodmanPluginError, match="WSL"):
            PodmanPlugin().check_and_download_plugin()
    mock_download_and_install.assert_not_called()


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._check_and_install_in_vm")
@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_and_install")
@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanVM.default")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_uses_the_vm_on_macos(mock_setting_get_instance, mock_vm_default,
                                                       mock_download_and_install, mock_check_and_install_in_vm):
    mock_setting_get_instance.return_value.api_socket_url = None
    with mock.patch.object(sys, "platform", "darwin"):
        PodmanPlugin().check_and_download_plugin()
    mock_check_and_install_in_vm.assert_called_once_with(mock_vm_default.return_value)
    mock_download_and_install.assert_not_called()


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._restart_podman_service")
@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._ensure_plugin_dir_configured", return_value=False)
@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_and_install")
@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._installed_version", return_value=None)
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_installs_on_linux(mock_setting_get_instance, mock_installed_version,
                                                     mock_download_and_install, mock_ensure_plugin_dir_configured,
                                                     mock_restart_podman_service):
    mock_setting_get_instance.return_value.api_socket_url = None
    with mock.patch.object(sys, "platform", "linux"):
        PodmanPlugin().check_and_download_plugin()
    mock_download_and_install.assert_called_once()
    mock_restart_podman_service.assert_called_once()