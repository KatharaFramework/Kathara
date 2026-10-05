import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.model.Link import Link
from src.Kathara.types import CollisionDomainTypesOption


@pytest.fixture()
def link():
    return Link(Lab("default_scenario"), "A")


def test_link_default_type(link):
    assert link.type is None


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
