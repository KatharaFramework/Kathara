import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.exceptions import InterfaceMacAddressError, InterfaceVlanError
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Interface import Interface
from src.Kathara.model.Link import Link

sys.path.insert(0, './src')


@pytest.fixture()
def default_device():
    return Machine(Lab("test_lab"), "test_machine")


@pytest.fixture()
def default_link(default_device):
    return Link(default_device.lab, "A")


def test_normal_iface(default_device: Machine, default_link: Link):
    interface = Interface(default_device, default_link, 0)

    assert interface.machine == default_device
    assert interface.link == default_link
    assert interface.num == 0
    assert interface.mac_address is None


def test_iface_num(default_device: Machine, default_link: Link):
    interface = Interface(default_device, default_link, 2)

    assert interface.machine == default_device
    assert interface.link == default_link
    assert interface.num == 2
    assert interface.mac_address is None


def test_iface_mac_address(default_device: Machine, default_link: Link):
    interface = Interface(default_device, default_link, 0, "00:00:00:00:00:01")

    assert interface.machine == default_device
    assert interface.link == default_link
    assert interface.num == 0
    assert interface.mac_address == "00:00:00:00:00:01"


def test_iface_num_and_mac_address(default_device: Machine, default_link: Link):
    interface = Interface(default_device, default_link, 2, "00:00:00:00:00:01")

    assert interface.machine == default_device
    assert interface.link == default_link
    assert interface.num == 2
    assert interface.mac_address == "00:00:00:00:00:01"


def test_iface_mac_address_error_short(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceMacAddressError):
        Interface(default_device, default_link, 0, "00:00:00:00:00")


def test_iface_mac_address_error_long(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceMacAddressError):
        Interface(default_device, default_link, 0, "00:00:00:00:00:00:00")


def test_iface_mac_address_error_invalid_sep(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceMacAddressError):
        Interface(default_device, default_link, 0, "00:00-00:00:00:00:00")


def test_iface_mac_address_invalid_val(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceMacAddressError):
        Interface(default_device, default_link, 0, "gg:00:00:00:00:00:00")


def test_iface_mac_address_invalid_format(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceMacAddressError):
        Interface(default_device, default_link, 0, "f:00:00:00:00:00:00")


def test_iface_no_vlans(default_device: Machine, default_link: Link):
    interface = Interface(default_device, default_link, 0)

    assert interface.vlan is None
    assert interface.tagged_vlans == []
    assert not interface.has_vlans()
    interface.check_vlans()


def test_iface_vlans(default_device: Machine, default_link: Link):
    default_link.mode = "managed"
    interface = Interface(default_device, default_link, 0, vlan=10, tagged_vlans=[30, 20, 30])

    assert interface.vlan == 10
    assert interface.tagged_vlans == [20, 30]
    assert interface.has_vlans()
    interface.check_vlans()


@pytest.mark.parametrize("vlan", [0, 4095, -1, "10", 1.5, True])
def test_iface_vlan_error(default_device: Machine, default_link: Link, vlan):
    with pytest.raises(InterfaceVlanError):
        Interface(default_device, default_link, 0, vlan=vlan)


def test_iface_tagged_vlan_error(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceVlanError):
        Interface(default_device, default_link, 0, tagged_vlans=[10, 5000])


def test_iface_vlan_both_untagged_and_tagged_error(default_device: Machine, default_link: Link):
    with pytest.raises(InterfaceVlanError):
        Interface(default_device, default_link, 0, vlan=10, tagged_vlans=[10, 20])


@pytest.mark.parametrize("mode", [None, "hub", "switch"])
def test_iface_check_vlans_not_managed_error(default_device: Machine, default_link: Link, mode):
    default_link.mode = mode
    interface = Interface(default_device, default_link, 0, vlan=10)

    with pytest.raises(InterfaceVlanError):
        interface.check_vlans()
