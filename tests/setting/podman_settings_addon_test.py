import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.exceptions import SettingsError
from src.Kathara.setting.addon.PodmanSettingsAddon import PodmanSettingsAddon, DEFAULTS


def test_network_plugin_default():
    addon = PodmanSettingsAddon()

    assert addon.network_plugin == "katharanp_vde"
    assert DEFAULTS["network_plugin"] == "katharanp_vde"
    assert addon.merge()["network_plugin"] == "katharanp_vde"


@pytest.mark.parametrize("plugin", ["katharanp_vde", "katharanp"])
def test_network_plugin_round_trip(plugin):
    addon = PodmanSettingsAddon()
    addon.load({"network_plugin": plugin})
    assert addon.network_plugin == plugin

    saved = addon.merge({})
    other = PodmanSettingsAddon()
    other.load(saved)
    assert other.network_plugin == plugin


@pytest.mark.parametrize("plugin", ["kathara/katharanp", "bridge", None])
def test_network_plugin_invalid(plugin):
    addon = PodmanSettingsAddon()

    with pytest.raises(SettingsError):
        addon.load({"network_plugin": plugin})
    with pytest.raises(SettingsError):
        addon.network_plugin = plugin

    assert addon.network_plugin == "katharanp_vde"
