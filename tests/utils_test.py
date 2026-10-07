import sys

sys.path.insert(0, './')

import pytest

from src.Kathara.utils import parse_docker_engine_version, parse_interface_definition


def test_docker_engine_version_numbers_only():
    assert parse_docker_engine_version('20.10.05') == '20.10.05'


def test_docker_engine_version_debian_str_plus():
    assert parse_docker_engine_version('20.10.5+dfsg1') == '20.10.5'


def test_docker_engine_version_debian_str_tilde():
    assert parse_docker_engine_version('20.10.5~dfsg1') == '20.10.5'


def test_docker_engine_version_debian_str_nosep():
    assert parse_docker_engine_version('20.10.5dfsg1') == '20.10.5'


@pytest.mark.parametrize("value,expected", [
    ("A", ("A", None, {})),
    ("A/00:00:00:00:00:01", ("A", "00:00:00:00:00:01", {})),
    ("A/vlan=10", ("A", None, {'vlan': 10})),
    ("A/trunk=10", ("A", None, {'tagged_vlans': [10]})),
    ("A/trunk=10,20", ("A", None, {'tagged_vlans': [10, 20]})),
    ("A/00:00:00:00:00:01/vlan=10/trunk=20,30", ("A", "00:00:00:00:00:01", {'vlan': 10, 'tagged_vlans': [20, 30]})),
    ("A/trunk=20/vlan=10", ("A", None, {'vlan': 10, 'tagged_vlans': [20]})),
])
def test_parse_interface_definition(value, expected):
    assert parse_interface_definition(value) == expected


@pytest.mark.parametrize("value", [
    "A/", "/A", "A//vlan=10", "A/vlan=ten", "A/vlan=", "A/trunk=", "A/trunk=10,", "A/vlan=10/vlan=20",
    "A/vlan=10/00:00:00:00:00:01", "A/00:00:00:00:00:01/00:00:00:00:00:02", "A/mtu=1500"
])
def test_parse_interface_definition_error(value):
    with pytest.raises(SyntaxError):
        parse_interface_definition(value)
