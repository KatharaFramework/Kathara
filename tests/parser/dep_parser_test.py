import pytest
import sys

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
