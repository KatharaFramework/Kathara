import logging
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
    with pytest.raises(SyntaxError):
        ExtParser.parse("tests/parser/labext/syntax_error")


def test_io_error():
    with pytest.raises(ValueError):
        ExtParser.parse("tests/parser/labext/value_error")


def _write_ext(tmp_path, content):
    (tmp_path / "lab.ext").write_text(content)
    return str(tmp_path)


def test_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        ExtParser.parse(str(tmp_path))


def test_empty_file(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert ExtParser.parse(_write_ext(tmp_path, "")) is None

    assert "lab.ext file is empty" in caplog.text


def test_only_comments_and_empty_lines(tmp_path):
    assert ExtParser.parse(_write_ext(tmp_path, "# comment\n\n   \n")) == {}


def test_comments_and_empty_lines_between_entries(tmp_path):
    external_links = ExtParser.parse(_write_ext(tmp_path, "# first\nA eth0\n\n# second\nB eth1.20\n"))
    assert set(external_links.keys()) == {'A', 'B'}


@pytest.mark.parametrize("separator", [" ", "   ", "\t"])
def test_separators(tmp_path, separator):
    external_links = ExtParser.parse(_write_ext(tmp_path, f"A{separator}eth0\n"))
    assert external_links['A'][0].interface == 'eth0'


def test_last_line_without_newline(tmp_path):
    external_links = ExtParser.parse(_write_ext(tmp_path, "A eth0\nB eth1.20"))
    assert external_links['B'][0].interface == 'eth1'
    assert external_links['B'][0].vlan == 20


@pytest.mark.parametrize("vlan", [1, 4094])
def test_vlan_boundaries(tmp_path, vlan):
    external_links = ExtParser.parse(_write_ext(tmp_path, f"A eth0.{vlan}\n"))
    assert external_links['A'][0].vlan == vlan


@pytest.mark.parametrize("vlan", [0, 4095])
def test_vlan_out_of_range(tmp_path, vlan):
    with pytest.raises(ValueError, match=r"line 1: VLAN ID must be in range \[1, 4094\]"):
        ExtParser.parse(_write_ext(tmp_path, f"A eth0.{vlan}\n"))


def test_value_error_reports_line_number(tmp_path):
    with pytest.raises(ValueError, match="line 3"):
        ExtParser.parse(_write_ext(tmp_path, "A eth0\n# comment\nB eth1.5000\n"))


@pytest.mark.parametrize("line", [
    "A",  # no interface
    "eth0",  # no collision domain
    "A=eth0",  # wrong separator
    "A eth0 eth1",  # two interfaces on the same line
    "A eth0.",  # dot without VLAN
    "A eth0.ab",  # non numeric VLAN
    "A eth0.1.2",  # two VLAN tags
])
def test_malformed_line(tmp_path, line):
    with pytest.raises(SyntaxError):
        ExtParser.parse(_write_ext(tmp_path, f"{line}\n"))


def test_syntax_error_reports_line_number(tmp_path):
    with pytest.raises(SyntaxError, match="Line 2"):
        ExtParser.parse(_write_ext(tmp_path, "A eth0\nnot valid line here\n"))


def test_same_interface_on_different_collision_domains(tmp_path):
    external_links = ExtParser.parse(_write_ext(tmp_path, "A eth0.10\nB eth0.20\n"))
    assert external_links['A'][0].vlan == 10
    assert external_links['B'][0].vlan == 20
