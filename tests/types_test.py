import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.types import SharedCollisionDomainsOption, CollisionDomainTypesOption


def test_shared_collision_domains_option_to_string():
    assert SharedCollisionDomainsOption.to_string(1) == 'Not Shared'
    assert SharedCollisionDomainsOption.to_string(2) == 'Share collision domains between network scenarios'
    assert SharedCollisionDomainsOption.to_string(3) == 'Share collision domains between users'


def test_shared_collision_domains_option_to_string_unknown_value():
    assert SharedCollisionDomainsOption.to_string(4) is None


def test_collision_domain_types_option_values():
    assert CollisionDomainTypesOption.BRIDGE == "bridge"
    assert CollisionDomainTypesOption.HUB == "hub"
    assert CollisionDomainTypesOption.P2P == "p2p"
    assert {x.value for x in CollisionDomainTypesOption} == {"bridge", "hub", "p2p"}


def test_collision_domain_types_option_parse():
    assert CollisionDomainTypesOption.parse("bridge") is CollisionDomainTypesOption.BRIDGE
    assert CollisionDomainTypesOption.parse("hub") is CollisionDomainTypesOption.HUB
    assert CollisionDomainTypesOption.parse("p2p") is CollisionDomainTypesOption.P2P


def test_collision_domain_types_option_parse_invalid():
    with pytest.raises(ValueError, match="Invalid collision domain type `switch`"):
        CollisionDomainTypesOption.parse("switch")
