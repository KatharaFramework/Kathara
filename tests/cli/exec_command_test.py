import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.docker.exec_stream.DockerExecStream import DockerExecStream
from src.Kathara.cli.command.ExecCommand import ExecCommand
from src.Kathara.model.Lab import Lab


@pytest.fixture
@mock.patch("docker.client.DockerClient")
def exec_output(client_mock):
    def output_generator():
        yield 'stdout'.encode(), 'stderr'.encode()

    return DockerExecStream(output_generator(), "id", client_mock)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_params(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab,
                       mock_docker_manager, mock_manager_get_instance, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')
    exec_output._client.api.exec_inspect.assert_called_once_with('id')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_error_exit_code(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab,
                             mock_docker_manager, mock_manager_get_instance, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    exec_output._client.api.exec_inspect.return_value = {'ExitCode': 1}
    command = ExecCommand()
    code = command.run('.', ['pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')
    exec_output._client.api.exec_inspect.assert_called_once_with('id')
    assert code == 1


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_with_directory_absolute_path(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab,
                                          mock_docker_manager, mock_manager_get_instance,
                                          exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['-d', os.path.join('/test', 'path'), 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')
    exec_output._client.api.exec_inspect.assert_called_once_with('id')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_with_directory_relative_path(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab,
                                          mock_docker_manager, mock_manager_get_instance,
                                          exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['-d', os.path.join('test', 'path'), 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), 'test', 'path'))
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')
    exec_output._client.api.exec_inspect.assert_called_once_with('id')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_with_v_option(mock_stderr_write, mock_stdout_write, mock_parse_lab, mock_docker_manager,
                           mock_manager_get_instance, exec_output):
    mock_manager_get_instance.return_value = mock_docker_manager
    lab = Lab('kathara_vlab')
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['-v', 'pc1', 'test command'])
    assert not mock_parse_lab.called
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=lab.hash, wait=False)
    mock_stdout_write.assert_called_once_with('stdout')
    mock_stderr_write.assert_called_once_with('stderr')
    exec_output._client.api.exec_inspect.assert_called_once_with('id')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_stdout(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_docker_manager,
                       mock_manager_get_instance, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['--no-stdout', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    assert not mock_stdout_write.called
    mock_stderr_write.assert_called_once_with('stderr')
    exec_output._client.api.exec_inspect.assert_called_once_with('id')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_stderr(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_docker_manager,
                       mock_manager_get_instance, exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['--no-stderr', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    mock_stdout_write.assert_called_once_with('stdout')
    assert not mock_stderr_write.called
    exec_output._client.api.exec_inspect.assert_called_once_with('id')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
@mock.patch('sys.stderr.write')
def test_run_no_stdout_no_stderr(mock_stderr_write, mock_stdout_write, mock_lab, mock_parse_lab, mock_docker_manager,
                                 mock_manager_get_instance,
                                 exec_output):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec.return_value = exec_output
    command = ExecCommand()
    command.run('.', ['--no-stdout', '--no-stderr', 'pc1', 'test command'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.exec.assert_called_once_with("pc1", 'test command', lab_hash=mock_lab.hash, wait=False)
    assert not mock_stdout_write.called
    assert not mock_stderr_write.called
    exec_output._client.api.exec_inspect.assert_called_once_with('id')
