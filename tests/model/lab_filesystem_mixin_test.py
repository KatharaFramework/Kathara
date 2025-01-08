import os
import sys
from unittest import mock

import fs
import pytest

sys.path.insert(0, './')

from src.Kathara.foundation.model.LabFilesystemMixin import LabFilesystemMixin
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine


@pytest.fixture()
def default_device():
    return Machine(Lab("test_lab"), "test_machine")


#
# TEST: create_file_from_string
#
@mock.patch("Kathara.foundation.model.FilesystemMixin.FilesystemMixin.create_file_from_string")
def test_create_startup_file_from_string(mock_create_file_from_string, default_device):
    filesystem = LabFilesystemMixin()
    filesystem.create_file_from_string = mock_create_file_from_string
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_startup_file_from_string(default_device, "commands")
    mock_create_file_from_string.assert_called_once_with("commands", f"{default_device.name}.startup")


@mock.patch("Kathara.foundation.model.FilesystemMixin.FilesystemMixin.create_file_from_list")
def test_create_startup_file_from_list(mock_create_file_from_list, default_device):
    filesystem = LabFilesystemMixin()
    filesystem.create_file_from_list = mock_create_file_from_list
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_startup_file_from_list(default_device, ["commands"])
    mock_create_file_from_list.assert_called_once_with(["commands"], f"{default_device.name}.startup")


@mock.patch("Kathara.foundation.model.FilesystemMixin.FilesystemMixin.create_file_from_stream")
def test_create_startup_file_from_stream(mock_create_file_from_stream, default_device):
    filesystem = LabFilesystemMixin()
    filesystem.create_file_from_stream = mock_create_file_from_stream
    filesystem.fs = fs.open_fs(f"mem://")
    with open(os.path.abspath(__file__), "rb") as stream:
        filesystem.create_startup_file_from_stream(default_device, stream)
    mock_create_file_from_stream.assert_called_once_with(stream, f"{default_device.name}.startup")


@mock.patch("Kathara.foundation.model.FilesystemMixin.FilesystemMixin.create_file_from_path")
def test_create_startup_file_from_path(mock_create_file_from_path, default_device):
    filesystem = LabFilesystemMixin()
    filesystem.create_file_from_path = mock_create_file_from_path
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_startup_file_from_path(default_device, "path")
    mock_create_file_from_path.assert_called_once_with("path", f"{default_device.name}.startup")


@mock.patch("Kathara.foundation.model.FilesystemMixin.FilesystemMixin.create_file_from_string")
def test_update_startup_file_from_string(mock_update_file_from_string, default_device):
    filesystem = LabFilesystemMixin()
    filesystem.update_file_from_string = mock_update_file_from_string
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.update_startup_file_from_string(default_device, "commands")
    mock_update_file_from_string.assert_called_once_with("commands", f"{default_device.name}.startup")


@mock.patch("Kathara.foundation.model.FilesystemMixin.FilesystemMixin.create_file_from_list")
def test_update_startup_file_from_list(mock_update_file_from_list, default_device):
    filesystem = LabFilesystemMixin()
    filesystem.update_file_from_list = mock_update_file_from_list
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.update_startup_file_from_list(default_device, ["commands"])
    mock_update_file_from_list.assert_called_once_with(["commands"], f"{default_device.name}.startup")
