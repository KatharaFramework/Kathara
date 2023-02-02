import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.ExecCommand import ExecCommand
from src.Kathara.model.Lab import Lab


@pytest.fixture
def exec_output():
    def output_generator():
        yield 'stdout'.encode(), 'stderr'.encode()

    return output_generator()


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_params(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_exec, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=mock_lab.hash)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_with_directory_absolute_path(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_exec,
                                          exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['-d', '/test/path', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with('/test/path')
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=mock_lab.hash)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_with_directory_relative_path(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_exec,
                                          exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['-d', 'test/path', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), 'test/path'))
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=mock_lab.hash)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_with_v_option(mock_stderr_write, mock_stdout_write, mock_parse_lab, mock_exec, exec_output):
    lab = Lab('kathara_vlab')
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['-v', 'pc1', 'test command'])
    assert not mock_parse_lab.called
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=lab.hash)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_stdout(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_exec, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['--no-stdout', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=mock_lab.hash)
    assert not mock_stdout_write.called
    mock_stderr_write.assert_called_once_with('stderr')


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_stderr(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_exec, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['--no-stderr', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=mock_lab.hash)
    mock_stdout_write.assert_called_once_with('stdout')
    assert not mock_stderr_write.called


@mock.patch("src.Kathara.manager.Kathara.Kathara.exec")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_stdout_no_stderr(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_exec,
                                 exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['--no-stdout', '--no-stderr', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_exec.assert_called_once_with("pc1", ['test command'], lab_hash=mock_lab.hash)
    assert not mock_stdout_write.called
    assert not mock_stderr_write.called
