import logging
import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.LinkParser import LinkParser


def test_link_types_and_external_links():
    link_metas = LinkParser.parse("tests/parser/lablink/full")
    assert set(link_metas.keys()) == {'A', 'B', 'C'}
    assert link_metas['A']['type'] == 'p2p'
    assert link_metas['B']['type'] == 'hub'
    assert link_metas['C'] == {'type': 'bridge'}
    assert len(link_metas['A']['external']) == 2
    assert len(link_metas['B']['external']) == 1
    assert link_metas['A']['external'][0].interface == 'enp0s25'
    assert link_metas['A']['external'][0].vlan is None
    assert link_metas['A']['external'][1].interface == 'enp0s25'
    assert link_metas['A']['external'][1].vlan == 30
    assert link_metas['B']['external'][0].interface == 'enp0s25'
    assert link_metas['B']['external'][0].vlan == 12


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        LinkParser.parse("tests/parser/lablink")


def test_empty_file(caplog):
    with caplog.at_level(logging.WARNING):
        assert LinkParser.parse("tests/parser/lablink/empty") == {}

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
        link_metas = LinkParser.parse("tests/parser/lablink/duplicate_type")

    assert link_metas == {'A': {'type': 'hub'}}
    assert "already has a type assigned" in caplog.text


def test_same_type_twice_does_not_warn(tmp_path, caplog):
    (tmp_path / "lab.link").write_text('A[type]="p2p"\nA[type]="p2p"\n')
    with caplog.at_level(logging.WARNING):
        link_metas = LinkParser.parse(str(tmp_path))

    assert link_metas == {'A': {'type': 'p2p'}}
    assert "already has a type assigned" not in caplog.text


def test_external_only_collision_domain(tmp_path):
    # Regression: a collision domain without `type` must not raise KeyError
    (tmp_path / "lab.link").write_text('A[external]="eth0"\nA[type]="hub"\nB[type]="p2p"\n')
    link_metas = LinkParser.parse(str(tmp_path))

    assert link_metas['A']['type'] == 'hub'
    assert link_metas['A']['external'][0].interface == 'eth0'
    assert link_metas['B'] == {'type': 'p2p'}


def test_bridge_metas(tmp_path):
    # Values are validated when assigned to the collision domain, the parser keeps them as strings
    (tmp_path / "lab.link").write_text('A[type]="bridge"\nA[ageing_time]="30000"\nA[group_fwd_mask]=0x4000\n')
    link_metas = LinkParser.parse(str(tmp_path))

    assert link_metas == {'A': {'type': 'bridge', 'ageing_time': '30000', 'group_fwd_mask': '0x4000'}}


def test_bridge_meta_overwritten_warns(tmp_path, caplog):
    (tmp_path / "lab.link").write_text('A[ageing_time]=100\nA[ageing_time]=200\nA[ageing_time]=200\n')
    with caplog.at_level(logging.WARNING):
        link_metas = LinkParser.parse(str(tmp_path))

    assert link_metas == {'A': {'ageing_time': '200'}}
    # Only the change from 100 to 200 is reported
    assert caplog.text.count("already has `ageing_time` assigned") == 1


def test_ageing_type_is_not_supported(tmp_path):
    (tmp_path / "lab.link").write_text('A[ageing_type]=100\n')
    with pytest.raises(SyntaxError, match="Invalid argument `ageing_type`"):
        LinkParser.parse(str(tmp_path))
