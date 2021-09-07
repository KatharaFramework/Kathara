import pytest
import sys

sys.path.insert(0, './')

from src.Kathara.model.ExternalLink import ExternalLink


@pytest.fixture()
def external_link_vlan():
    return ExternalLink("eth0", 1)


@pytest.fixture()
def external_link_no_vlan():
    return ExternalLink("eth0", )


def test_external_link_creation(external_link_vlan):
    assert external_link_vlan.interface == "eth0"
    assert external_link_vlan.vlan == 1


def test_get_name_and_vlan(external_link_vlan):
    interface, vlan = external_link_vlan.get_name_and_vlan()
    assert interface == "eth0"
    assert vlan is 1


def test_get_name_and_vlan_no_vlan(external_link_no_vlan):
    interface, vlan = external_link_no_vlan.get_name_and_vlan()
    assert interface == "eth0"
    assert vlan is None


def test_get_name_and_vlan_long_name():
    external_link = ExternalLink("long-interface-name", 1)
    interface, vlan = external_link.get_name_and_vlan()
    # If the length of interface name + vlan tag is more than 15 chars, we truncate the interface name to
    # 15 - VLAN_NAME_LENGTH in order to fit the whole string in 15 chars
    assert interface == "long-interfac"
    assert vlan is 1


def test_full_name(external_link_vlan):
    full_name = external_link_vlan.get_full_name()
    assert full_name == "eth0.1"


def test_full_name_no_vlan(external_link_no_vlan):
    full_name = external_link_no_vlan.get_full_name()
    assert full_name == "eth0"



