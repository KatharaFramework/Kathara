import logging
import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.LinkParser import LinkParser


def test_link_types_and_external_links():
    link_types, external_links = LinkParser.parse("tests/parser/lablink/full")
    assert link_types == {'A': 'p2p', 'B': 'hub', 'C': 'bridge'}
    assert len(external_links) == 2
    assert len(external_links['A']) == 2
    assert len(external_links['B']) == 1
    assert external_links['A'][0].interface == 'enp0s25'
    assert external_links['A'][0].vlan is None
    assert external_links['A'][1].interface == 'enp0s25'
    assert external_links['A'][1].vlan == 30
    assert external_links['B'][0].interface == 'enp0s25'
    assert external_links['B'][0].vlan == 12


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        LinkParser.parse("tests/parser/lablink")


def test_empty_file(caplog):
    with caplog.at_level(logging.WARNING):
        assert LinkParser.parse("tests/parser/lablink/empty") == ({}, {})

    assert "lab.link file is empty" in caplog.text


def test_malformed_file():
    with pytest.raises(SyntaxError, match="Line 2"):
        LinkParser.parse("tests/parser/lablink/syntax_error")


def test_invalid_argument():
    with pytest.raises(SyntaxError, match="Invalid argument `speed`"):
        LinkParser.parse("tests/parser/lablink/invalid_arg")


def test_invalid_type():
    with pytest.raises(SyntaxError, match="Line 1: Invalid collision domain type `switch`"):
        LinkParser.parse("tests/parser/lablink/invalid_type")


def test_vlan_out_of_range():
    with pytest.raises(ValueError, match=r"line 1: VLAN ID must be in range"):
        LinkParser.parse("tests/parser/lablink/vlan_out_of_range")


def test_invalid_external_interface():
    with pytest.raises(SyntaxError, match="Line 1"):
        LinkParser.parse("tests/parser/lablink/invalid_external")


def test_duplicate_type_overwrites_and_warns(caplog):
    with caplog.at_level(logging.WARNING):
        link_types, external_links = LinkParser.parse("tests/parser/lablink/duplicate_type")

    assert link_types == {'A': 'hub'}
    assert external_links == {}
    assert "already has a type assigned" in caplog.text
