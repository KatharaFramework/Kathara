import builtins
import io
import os
import sys
from unittest import mock

import fs
import pytest

sys.path.insert(0, './')

from src.Kathara.foundation.model.FilesystemMixin import FilesystemMixin
from src.Kathara.exceptions import InvocationError


def test_fs_type_none():
    filesystem = FilesystemMixin()
    assert not filesystem.fs_type()


def test_fs_type_os():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"osfs://{os.getcwd()}")
    assert filesystem.fs_type() == "os"


def test_fs_type_mem():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    assert filesystem.fs_type() == "memory"


def test_fs_path_none():
    filesystem = FilesystemMixin()
    assert not filesystem.fs_path()


def test_fs_path_os():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"osfs://{os.getcwd()}")
    assert os.path.normpath(filesystem.fs_path()) == os.getcwd()


def test_fs_path_mem():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    assert filesystem.fs_path() is None


def test_create_file_from_string_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.create_file_from_string("test", "path")


def test_create_file_from_string():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
        filesystem.create_file_from_string("test", "/")
        mock_fs.makedirs.assert_called_once_with("/", recreate=True)
        mock_fs.open.assert_called_once_with("/", "w")


def test_create_file_from_list_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.create_file_from_list(["test"], "path")


def test_create_file_from_list():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
        filesystem.create_file_from_list(["test"], "/")
        mock_fs.makedirs.assert_called_once_with("/", recreate=True)
        mock_fs.open.assert_called_once_with("/", "w")


def test_create_file_from_path_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.create_file_from_path("/test", "path")


def test_create_file_from_path():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
        with mock.patch.object(builtins, "open") as mock_open:
            filesystem.create_file_from_path(os.path.abspath(__file__), "/")
            mock_fs.makedirs.assert_called_once_with("/", recreate=True)
            mock_open.assert_called_once_with(os.path.abspath(__file__), "rb")


def test_create_file_from_stream_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.create_file_from_stream(open(os.path.abspath(__file__), "r"), "path")


def test_create_file_from_stream():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with open(os.path.abspath(__file__), "r") as stream:
        with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
            filesystem.create_file_from_stream(stream, "/")
            mock_fs.makedirs.assert_called_once_with("/", recreate=True)
            mock_fs.open.assert_called_once_with("/", "w")


def test_create_file_from_stream_unsupported_operation():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with open(os.path.abspath(__file__), "a", encoding='utf-8') as stream:
        with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
            with pytest.raises(io.UnsupportedOperation):
                filesystem.create_file_from_stream(stream, "/")
            mock_fs.makedirs.assert_called_once_with("/", recreate=True)
            assert not mock_fs.upload.called
            mock_fs.open.assert_called_once_with("/", 'w')


def test_create_file_from_stream_byte():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with open(os.path.abspath(__file__), "rb") as stream:
        with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
            filesystem.create_file_from_stream(stream, "/")
        mock_fs.makedirs.assert_called_once_with("/", recreate=True)
        mock_fs.upload.assert_called_once_with("/", stream)
