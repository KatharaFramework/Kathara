import builtins
import io
import os
import sys
from unittest import mock

import fs
import pytest
from fs.errors import ResourceNotFound, FileExpected

sys.path.insert(0, './')

from src.Kathara.foundation.model.FilesystemMixin import FilesystemMixin
from src.Kathara.exceptions import InvocationError, LineNotFoundError


#
# TEST: fs_type
#
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


#
# TEST: fs_path
#
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


#
# TEST: create_file_from_string
#
def test_create_file_from_string_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.create_file_from_string("test", "path")


def test_create_file_from_string():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
        filesystem.create_file_from_string("test", "/test.txt")
        mock_fs.makedirs.assert_called_once_with("/", recreate=True)
        mock_fs.open.assert_called_once_with("/test.txt", "w")


#
# TEST: update_file_from_string
#
def test_update_file_from_string():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("te", "/test.txt")
    with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
        filesystem.update_file_from_string("st", "/test.txt")
        mock_fs.open.assert_called_once_with("/test.txt", "a")


def test_update_file_from_string_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.update_file_from_string("test", "path")


#
# TEST: create_file_from_list
#
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


#
# TEST: update_file_from_list
#
def test_update_file_from_list():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("te", "/test.txt")
    with mock.patch.object(FilesystemMixin, "fs") as mock_fs:
        filesystem.update_file_from_list(["st"], "/test.txt")
        mock_fs.open.assert_called_once_with("/test.txt", "a")


def test_update_file_from_list_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.update_file_from_list(["test"], "path")


#
# TEST: create_file_from_path
#
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


#
# TEST: create_file_from_stream
#
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


#
# TEST: write_line_before
#
def test_write_line_before():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("a\nb\nd", "test.txt")
    filesystem.write_line_before('test.txt', 'c', 'd')
    lines = filesystem.fs.open("test.txt", "r").readlines()
    assert len(lines) == 4
    assert lines[0].strip() == 'a'
    assert lines[1].strip() == 'b'
    assert lines[2].strip() == 'c'
    assert lines[3].strip() == 'd'


def test_write_line_before_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.write_line_before('test.txt', 'c', 'b')


def test_write_line_before_resource_not_found_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with pytest.raises(ResourceNotFound):
        filesystem.write_line_before('test.txt', 'c', 'b')


def test_write_line_before_file_expected_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.fs.makedir("test")
    with pytest.raises(FileExpected):
        filesystem.write_line_before('test', 'c', 'b')


def test_write_line_before_line_not_found_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("a\nb\nd", "test.txt")
    with pytest.raises(LineNotFoundError):
        filesystem.write_line_before('test.txt', 'c', 'z')


#
# TEST: write_line_after
#
def test_write_line_after():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("a\nb\nd", "test.txt")
    filesystem.write_line_after('test.txt', 'c', 'b')
    lines = filesystem.fs.open("test.txt", "r").readlines()
    assert len(lines) == 4
    assert lines[0].strip() == 'a'
    assert lines[1].strip() == 'b'
    assert lines[2].strip() == 'c'
    assert lines[3].strip() == 'd'


def test_write_line_after_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.write_line_after('test.txt', 'c', 'b')


def test_write_line_after_resource_not_found_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with pytest.raises(ResourceNotFound):
        filesystem.write_line_after('test.txt', 'c', 'b')


def test_write_line_after_file_expected_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.fs.makedir("test")
    with pytest.raises(FileExpected):
        filesystem.write_line_after('test', 'c', 'b')


def test_write_line_after_line_not_found_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("a\nb\nd", "test.txt")
    with pytest.raises(LineNotFoundError):
        filesystem.write_line_after('test.txt', 'c', 'z')


#
# TEST: delete_line
#
def test_delete_line():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("a\nb\nd", "test.txt")
    filesystem.delete_line('test.txt', 'b')
    lines = filesystem.fs.open("test.txt", "r").readlines()
    assert len(lines) == 2
    assert lines[0].strip() == 'a'
    assert lines[1].strip() == 'd'


def test_delete_line_invocation_error():
    filesystem = FilesystemMixin()
    with pytest.raises(InvocationError):
        filesystem.delete_line('test.txt', 'b')


def test_delete_line_resource_not_found_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    with pytest.raises(ResourceNotFound):
        filesystem.delete_line('test.txt', 'b')


def test_delete_line_file_expected_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.fs.makedir("test")
    with pytest.raises(FileExpected):
        filesystem.delete_line('test', 'b')


def test_delete_line_line_not_found_error():
    filesystem = FilesystemMixin()
    filesystem.fs = fs.open_fs(f"mem://")
    filesystem.create_file_from_string("a\nb\nd", "test.txt")
    with pytest.raises(LineNotFoundError):
        filesystem.delete_line('test.txt', 'z')
