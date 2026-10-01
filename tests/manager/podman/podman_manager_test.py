import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from podman.errors import APIError

sys.path.insert(0, './')

from src.Kathara.manager.podman.PodmanManager import PodmanManager, default_podman_socket
from src.Kathara.exceptions import ContainerEngineConnectionError, NotSupportedError
from src.Kathara.model.Lab import Lab


@pytest.fixture(autouse=True)
def rootless_user_and_no_plugin_install():
    # Every test runs as a normal user and never touches the real plugin installation.
    with mock.patch("src.Kathara.manager.podman.PodmanManager.utils.is_admin", return_value=False), \
            mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanPlugin") as mock_plugin:
        yield mock_plugin


def _setting_mock(**overrides):
    setting_mock = Mock()
    setting_mock.configure_mock(**{'api_socket_url': None, **overrides})
    return setting_mock


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_init_raises_on_ping_failure(mock_podman_client_cls, mock_setting_get_instance):
    mock_setting_get_instance.return_value = _setting_mock()
    client_instance = mock_podman_client_cls.return_value
    client_instance.ping.side_effect = APIError("boom")

    with pytest.raises(ContainerEngineConnectionError):
        PodmanManager()


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_init_raises_when_ping_returns_false(mock_podman_client_cls, mock_setting_get_instance):
    mock_setting_get_instance.return_value = _setting_mock()
    client_instance = mock_podman_client_cls.return_value
    client_instance.ping.return_value = False

    with pytest.raises(ContainerEngineConnectionError):
        PodmanManager()


@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanLink")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanMachine")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanImage")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_init_success(mock_podman_client_cls, mock_setting_get_instance, mock_image, mock_machine, mock_link,
                      rootless_user_and_no_plugin_install):
    mock_setting_get_instance.return_value = _setting_mock()
    client_instance = mock_podman_client_cls.return_value
    client_instance.ping.return_value = True

    manager = PodmanManager()

    assert manager.client == client_instance
    rootless_user_and_no_plugin_install.return_value.check_and_download_plugin.assert_called_once()


def test_get_formatted_manager_name():
    assert PodmanManager.get_formatted_manager_name() == "Podman (Kathara)"


@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanLink")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanMachine")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanImage")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_wipe_all_users_not_supported(mock_podman_client_cls, mock_setting_get_instance, mock_image, mock_machine,
                                      mock_link):
    mock_setting_get_instance.return_value = _setting_mock()
    client_instance = mock_podman_client_cls.return_value
    client_instance.ping.return_value = True

    manager = PodmanManager()

    with pytest.raises(NotSupportedError, match="Wiping the devices of all users"):
        manager.wipe(all_users=True)

    assert not mock_machine.return_value.wipe.called
    assert not mock_link.return_value.wipe.called


@pytest.fixture()
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanLink")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanMachine")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanImage")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def podman_manager(mock_podman_client_cls, mock_setting_get_instance, mock_image, mock_machine, mock_link):
    mock_setting_get_instance.return_value = _setting_mock()
    client_instance = mock_podman_client_cls.return_value
    client_instance.ping.return_value = True

    return PodmanManager()


@pytest.fixture()
def privileged_lab():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc1.add_meta("privileged", True)
    lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link("pc2", "A")
    return lab


def test_deploy_lab_privileged_not_supported(podman_manager, privileged_lab):
    with pytest.raises(NotSupportedError, match="Privileged devices"):
        podman_manager.deploy_lab(privileged_lab)

    assert not podman_manager.podman_link.deploy_links.called
    assert not podman_manager.podman_machine.deploy_machines.called
    assert not podman_manager.client.networks.create.called
    assert not podman_manager.client.containers.create.called


def test_deploy_lab_privileged_via_selected_machines_not_supported(podman_manager, privileged_lab):
    # `pc1` (privileged) is not excluded, so it is still going to be deployed.
    with pytest.raises(NotSupportedError, match="Privileged devices"):
        podman_manager.deploy_lab(privileged_lab, selected_machines={"pc1"})

    assert not podman_manager.podman_link.deploy_links.called
    assert not podman_manager.podman_machine.deploy_machines.called


def test_deploy_lab_privileged_excluded_not_raised(podman_manager, privileged_lab):
    # `pc1` (privileged) is excluded, so only `pc2` (not privileged) is going to be deployed.
    podman_manager.deploy_lab(privileged_lab, excluded_machines={"pc1"})

    podman_manager.podman_link.deploy_links.assert_called_once()
    podman_manager.podman_machine.deploy_machines.assert_called_once()


def test_deploy_machine_privileged_not_supported(podman_manager, privileged_lab):
    pc1 = privileged_lab.machines["pc1"]

    with pytest.raises(NotSupportedError, match="Privileged devices"):
        podman_manager.deploy_machine(pc1)

    assert not podman_manager.podman_link.deploy_links.called
    assert not podman_manager.podman_machine.deploy_machines.called
    assert not podman_manager.client.networks.create.called
    assert not podman_manager.client.containers.create.called


def test_default_podman_socket_rootless(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda path: False)
    monkeypatch.setattr("src.Kathara.manager.podman.PodmanManager.get_runtime_dir", lambda: "/run/user/1000")

    assert default_podman_socket() == "unix:///run/user/1000/podman/podman.sock"


def test_default_podman_socket_ignores_rootful_socket(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda path: path == "/run/podman/podman.sock")
    monkeypatch.setattr("src.Kathara.manager.podman.PodmanManager.get_runtime_dir", lambda: "/run/user/1000")

    assert default_podman_socket() == "unix:///run/user/1000/podman/podman.sock"


@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_init_rejects_root(mock_podman_client_cls, rootless_user_and_no_plugin_install):
    with mock.patch("src.Kathara.manager.podman.PodmanManager.utils.is_admin", return_value=True):
        with pytest.raises(NotSupportedError, match="without sudo"):
            PodmanManager()

    mock_podman_client_cls.assert_not_called()
    rootless_user_and_no_plugin_install.assert_not_called()


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_init_ping_failure_does_not_install_plugin(mock_podman_client_cls, mock_setting_get_instance,
                                                    rootless_user_and_no_plugin_install):
    mock_setting_get_instance.return_value = _setting_mock()
    mock_podman_client_cls.return_value.ping.return_value = False

    with pytest.raises(ContainerEngineConnectionError):
        PodmanManager()

    rootless_user_and_no_plugin_install.return_value.check_and_download_plugin.assert_not_called()


@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanLink")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanMachine")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanImage")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.podman.PodmanManager.PodmanClient")
def test_get_release_version_nested_shape(mock_podman_client_cls, mock_setting_get_instance, mock_image,
                                          mock_machine, mock_link):
    mock_setting_get_instance.return_value = _setting_mock()
    client_instance = mock_podman_client_cls.return_value
    client_instance.ping.return_value = True
    # libpod's native /version nests the version string, unlike Docker's flat shape.
    client_instance.version.return_value = {"Version": {"Version": "4.9.3", "APIVersion": "4.9.3"}}

    manager = PodmanManager()

    assert manager.get_release_version() == "4.9.3"
