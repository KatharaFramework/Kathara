import os
import sys
from unittest import mock
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath('./src'))

# `SettingsMenuFactory` must be imported before any `*OptionsHandler` module: its own
# import chain (SettingsMenuFactory -> CommonOptionsHandler -> OptionsHandler) is how the
# real `settings` command bootstraps the same modules without hitting the circular import
# that `OptionsHandler`/`SettingsMenuFactory`/`CommonOptionsHandler` would otherwise trigger
# if a `*OptionsHandler` module were the first of the three to be imported.
from Kathara.cli.ui.setting.SettingsMenuFactory import SettingsMenuFactory  # noqa: F401
from Kathara.cli.ui.setting.PodmanOptionsHandler import API_SOCKET_REGEX, PodmanOptionsHandler
from Kathara.foundation.cli.ui.setting.OptionsHandlerFactory import OptionsHandlerFactory
from Kathara.trdparty.consolemenu import ConsoleMenu, MenuFormatBuilder
from Kathara.trdparty.consolemenu.validators.regex import RegexValidator


def _build_menu():
    menu = ConsoleMenu(title="Kathara Settings")
    handler = PodmanOptionsHandler()
    with mock.patch("Kathara.setting.Setting.Setting.get_instance") as mock_get_instance:
        mock_get_instance.return_value = Mock(hosthome_mount=False, shared_mount=True,
                                              image_update_policy='Prompt', shared_cds=1,
                                              api_socket_url=None, network_plugin='katharanp_vde')
        handler.add_items(menu, MenuFormatBuilder())
    return menu


def _item_by_text(menu, text):
    return next(item for item in menu.items if item.get_text() == text)


def test_factory_creates_podman_options_handler():
    handler = OptionsHandlerFactory().create_instance(class_args=("Podman",))
    assert isinstance(handler, PodmanOptionsHandler)


def test_add_items_appends_expected_items():
    menu = _build_menu()

    titles = [item.get_text() for item in menu.items]
    assert titles == [
        "Choose Podman Network Plugin",
        "Automatically mount /hosthome on startup",
        "Automatically mount /shared on startup",
        "Podman Image Update Policy",
        "Enable Shared Collision Domains",
        "Configure a custom local Podman socket",
    ]


def test_network_plugin_submenu_choices():
    menu = _build_menu()

    network_plugin_item = _item_by_text(menu, "Choose Podman Network Plugin")
    choices = network_plugin_item.get_submenu().items

    assert [item.get_text() for item in choices] == ["katharanp_vde", "katharanp"]
    assert [item.args for item in choices] == [["network_plugin", "katharanp_vde"], ["network_plugin", "katharanp"]]


def test_shared_cds_submenu_has_only_two_choices():
    menu = _build_menu()

    shared_cds_item = _item_by_text(menu, "Enable Shared Collision Domains")
    submenu_items = shared_cds_item.get_submenu().items

    texts = [item.get_text() for item in submenu_items]
    assert texts == [
        "Share collision domains between network scenarios",
        "Do not share collision domains",
    ]


def test_socket_validator_accepts_local_unix_socket():
    validator = RegexValidator(API_SOCKET_REGEX)
    assert validator.validate("unix:///run/user/1000/podman/podman.sock") is True


def test_socket_validator_rejects_tcp():
    validator = RegexValidator(API_SOCKET_REGEX)
    assert validator.validate("tcp://127.0.0.1:8080") is False


def test_socket_validator_rejects_ssh():
    validator = RegexValidator(API_SOCKET_REGEX)
    assert validator.validate("ssh://user@remote/run/podman/podman.sock") is False


def test_socket_validator_rejects_relative_path():
    validator = RegexValidator(API_SOCKET_REGEX)
    assert validator.validate("unix://relative") is False
