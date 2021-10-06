import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.DepParser import DepParser


def test_three_devices_dependencies():
    dependencies = DepParser.parse("tests/parser/labdep/three_devices_dependencies")
    assert dependencies[0] == 'pc2' and dependencies[1] == 'pc3'


def test_devices_loop():
    with pytest.raises(Exception):
        DepParser.parse("tests/parser/labdep/devices_loop")
