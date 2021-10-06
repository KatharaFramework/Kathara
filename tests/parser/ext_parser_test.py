import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.ExtParser import ExtParser


def test_external_link():
    external_links = ExtParser.parse("tests/parser/labext/two_devices")
    assert len(external_links) == 2
    assert len(external_links['A']) == 2
    assert len(external_links['B']) == 1
    assert external_links['A'][0].interface == 'enp0s25'
    assert external_links['A'][0].vlan is None
    assert external_links['A'][1].interface == 'enp0s25'
    assert external_links['A'][1].vlan == 30
    assert external_links['B'][0].interface == 'enp0s25'
    assert external_links['B'][0].vlan == 12


def test_malformed_file():
    with pytest.raises(Exception):
        ExtParser.parse("tests/parser/labext/fail")
