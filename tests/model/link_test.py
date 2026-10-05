import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.exceptions import LinkModeError, InterfaceVlanError
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Link import Link
from src.Kathara.types import LinkMode


@pytest.fixture()
def default_lab():
    return Lab("test_lab")


def test_default_mode(default_lab: Lab):
    link = Link(default_lab, "A")

    assert link.mode is None
    assert not link.is_managed()


@pytest.mark.parametrize("value,expected", [
    ("hub", LinkMode.HUB), ("switch", LinkMode.SWITCH), ("managed", LinkMode.MANAGED), ("Managed", LinkMode.MANAGED),
    (LinkMode.SWITCH, LinkMode.SWITCH), (None, None)
])
def test_mode(default_lab: Lab, value, expected):
    link = Link(default_lab, "A", mode=value)
    assert link.mode == expected

    link = Link(default_lab, "B")
    link.mode = value
    assert link.mode == expected
    assert link.is_managed() == (expected == LinkMode.MANAGED)


@pytest.mark.parametrize("value", ["router", "", 1])
def test_mode_error(default_lab: Lab, value):
    with pytest.raises(LinkModeError):
        Link(default_lab, "A", mode=value)

    link = Link(default_lab, "A")
    with pytest.raises(LinkModeError):
        link.mode = value
    assert link.mode is None


def test_lab_new_link_mode(default_lab: Lab):
    assert default_lab.new_link("A", mode="switch").mode == LinkMode.SWITCH
    assert default_lab.new_link("B").mode is None
    assert default_lab.get_or_new_link("C").mode is None

    with pytest.raises(LinkModeError):
        default_lab.new_link("D", mode="router")


def test_lab_connect_machine_to_link_vlans(default_lab: Lab):
    default_lab.new_link("A", mode=LinkMode.MANAGED)
    _, interface = default_lab.connect_machine_to_link("pc1", "A", vlan=10, tagged_vlans=[20])

    assert interface.vlan == 10
    assert interface.tagged_vlans == [20]

    interface = default_lab.connect_machine_obj_to_link(default_lab.get_machine("pc1"), "B")
    assert not interface.has_vlans()

    default_lab.check_integrity()


def test_lab_check_integrity_vlans_not_managed_error(default_lab: Lab):
    default_lab.connect_machine_to_link("pc1", "A", vlan=10)

    with pytest.raises(InterfaceVlanError):
        default_lab.check_integrity()

    default_lab.get_link("A").mode = "managed"
    default_lab.check_integrity()
