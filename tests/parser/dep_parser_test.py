import logging
import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.DepParser import DepParser
from src.Kathara.exceptions import MachineDependencyError


def test_three_devices_dependencies():
    dependencies = DepParser.parse("tests/parser/labdep/three_devices_dependencies")
    assert dependencies[0] == 'pc2' and dependencies[1] == 'pc3'


def test_devices_loop():
    with pytest.raises(MachineDependencyError):
        DepParser.parse("tests/parser/labdep/devices_loop")


def test_with_comment():
    dependencies = DepParser.parse("tests/parser/labdep/comments_empty_lines")
    assert dependencies == ['r2', 'pc3', 'pc2', 'pc1']


def test_syntax_error():
    with pytest.raises(SyntaxError):
        DepParser.parse("tests/parser/labdep/syntax_error")


def _write_dep(tmp_path, content):
    (tmp_path / "lab.dep").write_text(content)
    return str(tmp_path)


def test_file_not_found(tmp_path):
    assert DepParser.parse(str(tmp_path)) is None


def test_empty_file(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert DepParser.parse(_write_dep(tmp_path, "")) is None

    assert "lab.dep file is empty" in caplog.text


def test_only_comments_and_empty_lines(tmp_path):
    assert DepParser.parse(_write_dep(tmp_path, "# comment\n\n   \n# another comment\n")) == []


def test_no_space_after_colon(tmp_path):
    assert DepParser.parse(_write_dep(tmp_path, "pc1:pc2\n")) == ['pc2', 'pc1']


def test_leading_and_trailing_whitespace_is_ignored(tmp_path):
    assert DepParser.parse(_write_dep(tmp_path, "  pc1: pc2   \n")) == ['pc2', 'pc1']


def test_single_dependency(tmp_path):
    assert DepParser.parse(_write_dep(tmp_path, "pc1: pc2\n")) == ['pc2', 'pc1']


def test_last_line_without_newline(tmp_path):
    assert DepParser.parse(_write_dep(tmp_path, "pc1: pc2\npc2: pc3")) == ['pc3', 'pc2', 'pc1']


@pytest.mark.parametrize("line", [
    "pc1",  # no colon
    "pc1:",  # no dependencies
    ": pc2",  # no device
    "pc1: pc2,pc3",  # wrong separator
    "pc-1: pc2",  # invalid character in device name
    "pc1: pc-2",  # invalid character in dependency name
    "pc1 : pc2",  # space before the colon
    "pc1: pc2: pc3",  # two colons
])
def test_malformed_line(tmp_path, line):
    with pytest.raises(SyntaxError):
        DepParser.parse(_write_dep(tmp_path, f"{line}\n"))


def test_syntax_error_reports_line_number(tmp_path):
    with pytest.raises(SyntaxError, match="Line 3"):
        DepParser.parse(_write_dep(tmp_path, "pc1: pc2\n# comment\nnot valid\n"))


def test_self_dependency_is_a_loop(tmp_path):
    with pytest.raises(MachineDependencyError):
        DepParser.parse(_write_dep(tmp_path, "pc1: pc1\n"))
