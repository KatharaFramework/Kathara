import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.parser.netkit.FolderParser import FolderParser


def test_one_device_folder():
    lab = FolderParser.parse("tests/parser/labfolder/one_device")
    assert len(lab.machines) == 1
    assert lab.machines['pc1']


def test_two_devices_folders():
    lab = FolderParser.parse("tests/parser/labfolder/two_devices")
    assert len(lab.machines) == 2
    assert lab.machines['pc1']
    assert lab.machines['pc2']


def test_ignore_shared_folder():
    lab = FolderParser.parse("tests/parser/labfolder/ignore_shared_folder")
    assert len(lab.machines) == 2
    assert lab.machines['pc1']
    assert lab.machines['pc2']
