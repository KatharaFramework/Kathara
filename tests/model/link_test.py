import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import LinkInvalidError, LinkOptionError
from src.Kathara.model.ExternalLink import ExternalLink
from src.Kathara.model.Link import Link
from src.Kathara.types import CollisionDomainTypesOption


@pytest.fixture()
def link():
    return Link(Lab("default_scenario"), "A")


def test_link_default_meta(link):
    assert link.meta == {'type': None, 'external': []}


def test_link_update_meta(link):
    external_link = ExternalLink("eth0")
    link.update_meta({'type': 'hub', 'external': [external_link]})
    assert link.meta['type'] == CollisionDomainTypesOption.HUB
    assert link.meta['external'] == [external_link]


def test_link_add_meta_external_appends(link):
    link.add_meta('external', [ExternalLink("eth0")])
    link.add_meta('external', [ExternalLink("eth1", 10)])
    assert [x.get_full_name() for x in link.meta['external']] == ["eth0", "eth1.10"]


def test_link_default_type(link):
    assert link.meta['type'] is None


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
    link.add_meta('type', value)
    assert link.meta['type'] == expected
    assert isinstance(link.meta['type'], CollisionDomainTypesOption)


def test_link_set_type_none_resets_it(link):
    link.add_meta('type', "p2p")
    link.add_meta('type', None)
    assert link.meta['type'] is None


@pytest.mark.parametrize("value", ["switch", "", "P2P", " p2p", 1, True])
def test_link_set_invalid_type(link, value):
    with pytest.raises(ValueError, match="Invalid collision domain type"):
        link.add_meta('type', value)


def test_link_set_invalid_type_keeps_previous_value(link):
    link.add_meta('type', "hub")
    with pytest.raises(ValueError):
        link.add_meta('type', "switch")

    assert link.meta['type'] == CollisionDomainTypesOption.HUB


def test_link_invalid_type_message_lists_supported_types(link):
    with pytest.raises(ValueError) as e:
        link.add_meta('type', "switch")

    for supported in ("bridge", "hub", "p2p"):
        assert f"`{supported}`" in str(e.value)


def test_link_repr_with_type(link):
    link.add_meta('type', "p2p")
    assert "p2p" in repr(link)


@pytest.mark.parametrize("link_type", [None, "bridge", "hub"])
def test_check_not_p2p_has_no_constraints(link_type):
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.add_meta('type', link_type)
    _connect(link, "pc1", "pc2", "pc3", "pc4")
    link.meta['external'].append(ExternalLink("eth0"))
    link.check()
    link.check(strict=False)


def test_check_p2p_two_endpoints():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.add_meta('type', "p2p")
    _connect(link, "pc1", "pc2")
    link.check()
    link.check(strict=False)


@pytest.mark.parametrize("machine_names", [[], ["pc1"]])
def test_check_p2p_less_than_two_endpoints(machine_names):
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.add_meta('type', "p2p")
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
    link.add_meta('type', "p2p")
    with pytest.raises(LinkInvalidError, match="found 3"):
        link.check()

    with pytest.raises(LinkInvalidError, match="found 3"):
        link.check(strict=False)


def test_check_p2p_with_external_link():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.add_meta('type', "p2p")
    _connect(link, "pc1", "pc2")
    link.meta['external'].append(ExternalLink("eth0"))
    with pytest.raises(LinkInvalidError, match="external"):
        link.check()

    with pytest.raises(LinkInvalidError, match="external"):
        link.check(strict=False)


def test_check_p2p_external_link_attached_before_type():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    _connect(link, "pc1", "pc2")
    lab.attach_external_links({"A": [ExternalLink("eth0")]})
    link.add_meta('type', "p2p")
    with pytest.raises(LinkInvalidError, match="external"):
        link.check()


def test_check_p2p_back_to_default_type_removes_constraints():
    lab = Lab("default_scenario")
    link = lab.get_or_new_link("A")
    link.add_meta('type', "p2p")
    _connect(link, "pc1")
    link.add_meta('type', None)
    link.check()


def test_add_meta_external_returns_previous_value(link):
    first = ExternalLink("eth0")
    link.add_meta('external', [first])
    old_value = link.add_meta('external', [ExternalLink("eth1")])

    # The previous value is not affected by the new interfaces
    assert old_value == [first]
    assert len(link.meta['external']) == 2


@pytest.mark.parametrize("value, expected", [
    (0, 0),  # FDB entries never age
    (1, 1),
    ("30000", 30000),
    (" 30000 ", 30000),
    ("0x10", 16),
    (2 ** 32 - 1, 2 ** 32 - 1),
])
def test_add_meta_ageing_time(link, value, expected):
    assert link.add_meta('ageing_time', value) is None
    assert link.meta['ageing_time'] == expected


@pytest.mark.parametrize("value", [-1, 2 ** 32, "-1", str(2 ** 32)])
def test_add_meta_ageing_time_out_of_range(link, value):
    with pytest.raises(LinkOptionError, match="between 0 and 4294967295"):
        link.add_meta('ageing_time', value)

    assert 'ageing_time' not in link.meta


@pytest.mark.parametrize("value", ["abc", "", "1.5", 1.5, True, None, "0xZZ"])
def test_add_meta_ageing_time_not_an_integer(link, value):
    with pytest.raises(LinkOptionError, match="is not an integer"):
        link.add_meta('ageing_time', value)


def test_add_meta_ageing_time_returns_previous_value(link):
    link.add_meta('ageing_time', 100)
    assert link.add_meta('ageing_time', 200) == 100
    assert link.meta['ageing_time'] == 200


@pytest.mark.parametrize("value, expected", [
    (0, 0),
    (8, 8),  # Bit 3 is the first one that can be set
    ("16384", 16384),
    ("0x4000", 0x4000),
    ("0XFFF8", 0xFFF8),  # Every bit except 0-2
    (2 ** 16 - 8, 2 ** 16 - 8),
])
def test_add_meta_group_fwd_mask(link, value, expected):
    link.add_meta('group_fwd_mask', value)
    assert link.meta['group_fwd_mask'] == expected


@pytest.mark.parametrize("value", [1, 2, 4, 7, "0x0001", 0xFFFF])
def test_add_meta_group_fwd_mask_restricted_bits(link, value):
    with pytest.raises(LinkOptionError, match="bits 0-2"):
        link.add_meta('group_fwd_mask', value)

    assert 'group_fwd_mask' not in link.meta


@pytest.mark.parametrize("value", [-8, 2 ** 16, "0x10000"])
def test_add_meta_group_fwd_mask_out_of_range(link, value):
    with pytest.raises(LinkOptionError, match="between 0 and 65535"):
        link.add_meta('group_fwd_mask', value)


@pytest.mark.parametrize("value", ["abc", "", "0x", True, None])
def test_add_meta_group_fwd_mask_not_an_integer(link, value):
    with pytest.raises(LinkOptionError, match="is not an integer"):
        link.add_meta('group_fwd_mask', value)


@pytest.mark.parametrize("meta", [{'ageing_time': 100}, {'group_fwd_mask': 8},
                                  {'ageing_time': 100, 'group_fwd_mask': 8}])
def test_check_bridge_metas_on_bridge(link, meta):
    link.add_meta('type', 'bridge')
    link.update_meta(meta)
    link.check(strict=False)


@pytest.mark.parametrize("link_type", [None, "hub", "p2p"])
@pytest.mark.parametrize("meta", [{'ageing_time': 100}, {'group_fwd_mask': 8}])
def test_check_bridge_metas_on_other_types(link, link_type, meta):
    link.add_meta('type', link_type)
    link.update_meta(meta)
    with pytest.raises(LinkInvalidError, match="only be used on `bridge`"):
        link.check(strict=False)


@pytest.mark.parametrize("link_type", [None, "bridge", "hub"])
def test_check_without_bridge_metas(link, link_type):
    link.add_meta('type', link_type)
    link.check()
