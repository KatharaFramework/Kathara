import base64
import json
import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.exceptions import PodmanPluginError
from src.Kathara.manager.podman.PodmanPlugin import PodmanPlugin
from src.Kathara.manager.podman.PodmanVM import PodmanVM


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


#
# TEST: _check_and_install_in_vm
#
DATA_DIR = "/var/home/core/.local/share"
CONFIG_DIR = "/var/home/core/.config"
INSTALL_DIR = f"{DATA_DIR}/kathara/katharanp"
DROPIN_PATH = f"{CONFIG_DIR}/containers/containers.conf.d/kathara.conf"


def fake_vm(raw_arch="x86_64", data_dir=DATA_DIR, config_dir=CONFIG_DIR, info=None, dropin=None):
    """A mocked PodmanVM whose `query` returns what the plugin check reads in the VM."""
    from src.Kathara.manager.podman.PodmanPlugin import PLUGIN_VERSION
    info = json.dumps({"version": PLUGIN_VERSION}) if info is None else info
    dropin = PodmanPlugin.plugin_dropin_content(f"{INSTALL_DIR}/bin") if dropin is None else dropin
    vm = mock.Mock(spec=PodmanVM)
    vm.name = "podman-machine-default"
    vm.query.return_value = [raw_arch, data_dir, config_dir, info, base64.b64encode(dropin.encode()).decode()]
    return vm


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_text")
def test_vm_plugin_up_to_date_does_nothing(mock_download_text):
    vm = fake_vm()
    PodmanPlugin()._check_and_install_in_vm(vm)
    vm.query.assert_called_once()
    vm.install_archive.assert_not_called()
    vm.write_file.assert_not_called()
    vm.restart_podman.assert_not_called()
    mock_download_text.assert_not_called()


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_text", return_value="abc123  file\n")
def test_vm_plugin_fresh_install(mock_download_text):
    from src.Kathara.manager.podman.PodmanPlugin import PLUGIN_VERSION, RELEASE_URL
    vm = fake_vm(raw_arch="aarch64", info="", dropin="")
    PodmanPlugin()._check_and_install_in_vm(vm)
    url = RELEASE_URL.format(version=PLUGIN_VERSION, arch="arm64")
    mock_download_text.assert_called_once_with(url + ".sha256")
    vm.install_archive.assert_called_once_with(url, "abc123", INSTALL_DIR, "katharanp")
    vm.write_file.assert_called_once_with(DROPIN_PATH, PodmanPlugin.plugin_dropin_content(f"{INSTALL_DIR}/bin"))
    vm.restart_podman.assert_called_once()


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_text", return_value="abc123  file\n")
def test_vm_plugin_old_version_reinstalls_only_the_bundle(mock_download_text):
    vm = fake_vm(info=json.dumps({"version": "v0.0.1"}))
    PodmanPlugin()._check_and_install_in_vm(vm)
    vm.install_archive.assert_called_once()
    vm.write_file.assert_not_called()
    vm.restart_podman.assert_called_once()


def test_vm_plugin_changed_dropin_is_rewritten():
    vm = fake_vm(dropin="[network]\nsomething else\n")
    PodmanPlugin()._check_and_install_in_vm(vm)
    vm.install_archive.assert_not_called()
    vm.write_file.assert_called_once_with(DROPIN_PATH, PodmanPlugin.plugin_dropin_content(f"{INSTALL_DIR}/bin"))
    vm.restart_podman.assert_called_once()


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanPlugin._download_text", return_value="abc123  file\n")
def test_vm_plugin_unreadable_info_and_dropin_are_treated_as_missing(mock_download_text):
    vm = fake_vm(info="garbage")
    vm.query.return_value[4] = "%%%not-base64"
    PodmanPlugin()._check_and_install_in_vm(vm)
    vm.install_archive.assert_called_once()
    vm.write_file.assert_called_once()
    vm.restart_podman.assert_called_once()


def test_vm_plugin_unsupported_architecture():
    vm = fake_vm(raw_arch="riscv64")
    with pytest.raises(PodmanPluginError, match="`riscv64` architecture"):
        PodmanPlugin()._check_and_install_in_vm(vm)
    vm.install_archive.assert_not_called()


@pytest.mark.parametrize("data_dir,config_dir", [("", CONFIG_DIR), (DATA_DIR, "")])
def test_vm_plugin_unreadable_directories(data_dir, config_dir):
    vm = fake_vm(data_dir=data_dir, config_dir=config_dir)
    with pytest.raises(PodmanPluginError, match="user directories"):
        PodmanPlugin()._check_and_install_in_vm(vm)
    vm.install_archive.assert_not_called()
    vm.write_file.assert_not_called()


@mock.patch("src.Kathara.manager.podman.PodmanPlugin.PodmanVM.default")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_check_and_download_plugin_rejects_remote_connections_first(mock_setting_get_instance, mock_vm_default):
    mock_setting_get_instance.return_value.api_socket_url = "ssh://core@localhost:22/run/podman.sock"
    with mock.patch.object(sys, "platform", "darwin"):
        with pytest.raises(PodmanPluginError, match="remote Podman connection"):
            PodmanPlugin().check_and_download_plugin()
    mock_vm_default.assert_not_called()