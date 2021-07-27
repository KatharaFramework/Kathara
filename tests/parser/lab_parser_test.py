import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.LabParser import LabParser


def test_one_device():
    lab = LabParser.parse("tests/parser/labconf/one_device")
    assert len(lab.machines) == 1
    assert len(lab.links) == 2
    assert lab.machines['pc1']
    assert len(lab.machines['pc1'].interfaces) == 2
    assert lab.machines['pc1'].interfaces[0].name == 'A'
    assert lab.machines['pc1'].interfaces[1].name == 'B'
    assert lab.machines['pc1'].meta['privileged']
    assert (1000, 'udp') in lab.machines['pc1'].meta['ports']
    assert lab.machines['pc1'].meta['ports'][(1000, 'udp')] == 2000
    assert (3000, 'tcp') in lab.machines['pc1'].meta['ports']
    assert lab.machines['pc1'].meta['ports'][(3000, 'tcp')] == 4000
    assert (3000, 'udp') in lab.machines['pc1'].meta['ports']
    assert lab.machines['pc1'].meta['ports'][(3000, 'udp')] == 5000
    assert lab.machines['pc1'].get_num_terms() == 2


def test_one_device_interface_name_error():
    with pytest.raises(Exception):
        LabParser.parse("tests/parser/labconf/one_device_interface_name_error")


def test_one_device_shared_name_error():
    with pytest.raises(Exception):
        LabParser.parse("tests/parser/labconf/one_device_shared_error")


def test_two_device_one_cd():
    lab = LabParser.parse("tests/parser/labconf/two_device_one_cd")
    assert len(lab.machines) == 2
    assert len(lab.links) == 1
    assert lab.machines['pc1']
    assert len(lab.machines['pc1'].interfaces) == 1
    assert lab.machines['pc1'].interfaces[0].name == 'A'
    assert lab.machines['pc2']
    assert len(lab.machines['pc2'].interfaces) == 1
    assert lab.machines['pc2'].interfaces[0].name == 'A'
