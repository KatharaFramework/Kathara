import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import LinkInvalidError
from src.Kathara.model.ExternalLink import ExternalLink
from src.Kathara.model.Link import Link
from src.Kathara.types import CollisionDomainTypesOption


@pytest.fixture()
def link():
    return Link(Lab("default_scenario"), "A")


def test_link_default_type(link):
    assert link.type is None


def _connect(link, *machine_names):
    for name in machine_names:
        link.lab.connect_machine_to_link(name, link.name)


@pytest.mark.parametrize("value, expected", [
    ("bridge", CollisionDomainTypesOption.BRIDGE),
    ("hub", CollisionDomainTypesOption.HUB),
    ("p2p", CollisionDomainTypesOption.P2P),
    (CollisionDomainTypesOption.P2P, CollisionDomainTypesOption.P2P),
])
def test_link_set_type(link, value, expected):
    link.type = value
    assert link.type == expected
    assert isinstance(link.type, CollisionDomainTypesOption)


def test_link_set_type_none_resets_it(link):
    link.type = "p2p"
    link.type = None
    assert link.type is None


@pytest.mark.parametrize("value", ["switch", "", "P2P", " p2p", 1, True])
def test_link_set_invalid_type(link, value):
    with pytest.raises(ValueError, match="Invalid collision domain type"):
        link.type = value


def test_link_set_invalid_type_keeps_previous_value(link):
    link.type = "hub"
    with pytest.raises(ValueError):
        link.type = "switch"

    assert link.type == CollisionDomainTypesOption.HUB


def test_link_invalid_type_message_lists_supported_types(link):
    with pytest.raises(ValueError) as e:
        link.type = "switch"

    for supported in ("bridge", "hub", "p2p"):
        assert f"`{supported}`" in str(e.value)


def test_link_repr_with_type(link):
    link.type = "p2p"
    assert "p2p" in repr(link)


@pytest.mark.parametrize("link_type", [None, "bridge", "hub"])
def test_check_not_p2p_has_no_constraints(link_type):
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.type = link_type
    _connect(link, "pc1", "pc2", "pc3", "pc4")
    link.external.append(ExternalLink("eth0"))
    link.check()
    link.check(strict=False)


def test_check_p2p_two_endpoints():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.type = "p2p"
    _connect(link, "pc1", "pc2")
    link.check()
    link.check(strict=False)


@pytest.mark.parametrize("machine_names", [[], ["pc1"]])
def test_check_p2p_less_than_two_endpoints(machine_names):
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.type = "p2p"
    _connect(link, *machine_names)
    with pytest.raises(LinkInvalidError, match="exactly two endpoints, found %d" % len(machine_names)):
        link.check()

    # Endpoints can be connected later
    link.check(strict=False)


def test_check_p2p_more_than_two_endpoints():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    # The type is set after the endpoints, so the check in `add_interface` cannot catch it
    _connect(link, "pc1", "pc2", "pc3")
    link.type = "p2p"
    with pytest.raises(LinkInvalidError, match="found 3"):
        link.check()

    with pytest.raises(LinkInvalidError, match="found 3"):
        link.check(strict=False)


def test_check_p2p_with_external_link():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.type = "p2p"
    _connect(link, "pc1", "pc2")
    link.external.append(ExternalLink("eth0"))
    with pytest.raises(LinkInvalidError, match="external"):
        link.check()

    with pytest.raises(LinkInvalidError, match="external"):
        link.check(strict=False)


def test_check_p2p_external_link_attached_before_type():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    _connect(link, "pc1", "pc2")
    lab.attach_external_links({"A": [ExternalLink("eth0")]})
    link.type = "p2p"
    with pytest.raises(LinkInvalidError, match="external"):
        link.check()


def test_check_p2p_back_to_default_type_removes_constraints():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.type = "p2p"
    _connect(link, "pc1")
    link.type = None
    link.check()
