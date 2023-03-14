import sys

import pytest

from src.Kathara.exceptions import MachineCollisionDomainError
from src.Kathara.parser.netkit.LabParser import LabParser

sys.path.insert(0, './')


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


def test_one_device_lab_description():
    lab = LabParser.parse("tests/parser/labconf/one_device_lab_description")
    assert lab.description == "Description"
    assert lab.version == "1.0"
    assert lab.author == "Author"
    assert lab.email == "test@email.org"
    assert lab.web == "https://www.lab-test.org/"


def test_one_device_interface_name_error():
    with pytest.raises(Exception):
        LabParser.parse("tests/parser/labconf/one_device_interface_name_error")


def test_one_device_shared_name_error():
    with pytest.raises(Exception):
        LabParser.parse("tests/parser/labconf/one_device_shared_error")


def test_one_device_same_collision_domain_error():
    with pytest.raises(MachineCollisionDomainError):
        LabParser.parse("tests/parser/labconf/one_device_same_collision_domain_error")


def test_two_device_one_cd():
    lab = LabParser.parse("tests/parser/labconf/two_devices_one_cd")
    assert len(lab.machines) == 2
    assert len(lab.links) == 1
    assert lab.machines['pc1']
    assert len(lab.machines['pc1'].interfaces) == 1
    assert lab.machines['pc1'].interfaces[0].name == 'A'
    assert lab.machines['pc2']
    assert len(lab.machines['pc2'].interfaces) == 1
    assert lab.machines['pc2'].interfaces[0].name == 'A'


def test_inline_comment():
    lab = LabParser.parse("tests/parser/labconf/inline_comment")
    assert len(lab.machines) == 1
    assert len(lab.links) == 1
    assert lab.machines['pc1']
    assert len(lab.machines['pc1'].interfaces) == 1
    assert lab.machines['pc1'].interfaces[0].name == 'A'


def test_inline_comment_error():
    with pytest.raises(SyntaxError):
        LabParser.parse("tests/parser/labconf/inline_comment_error")


def test_unmatched_quotes():
    with pytest.raises(SyntaxError):
        LabParser.parse("tests/parser/labconf/unmatched_quotes")


def test_unclosed_quotes():
    with pytest.raises(SyntaxError):
        LabParser.parse("tests/parser/labconf/unclosed_quotes")
