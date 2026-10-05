import os
import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.SwitchCommand import SwitchCommand
from src.Kathara.exceptions import LinkCommandError
from src.Kathara.model.Lab import Lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
def test_run_command(mock_stdout_write, mock_lab, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec_link.return_value = "VLAN 0010"
    command = SwitchCommand()
    exit_code = command.run('.', ['A', 'vlan/print'])
    assert exit_code == 0
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.exec_link.assert_called_once_with("A", "vlan/print", lab_hash=mock_lab.hash)
    mock_stdout_write.assert_called_once_with("VLAN 0010\n")


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
def test_run_command_with_arguments_and_directory(mock_stdout_write, mock_lab, mock_parse_lab, mock_docker_manager,
                                                  mock_manager_get_instance):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec_link.return_value = ""
    command = SwitchCommand()
    exit_code = command.run('.', ['-d', os.path.join('/test', 'path'), 'A', 'port/setvlan', '3', '10'])
    assert exit_code == 0
    mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
    mock_docker_manager.exec_link.assert_called_once_with("A", "port/setvlan 3 10", lab_hash=mock_lab.hash)
    assert not mock_stdout_write.called


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch('sys.stdout.write')
def test_run_command_vmachine(mock_stdout_write, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec_link.return_value = "VLAN 0010"
    command = SwitchCommand()
    exit_code = command.run('.', ['-v', 'A', 'vlan/print'])
    assert exit_code == 0
    assert not mock_parse_lab.called
    mock_docker_manager.exec_link.assert_called_once_with("A", "vlan/print", lab_hash=Lab("kathara_vlab").hash)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stderr.write')
@mock.patch('sys.stdout.write')
def test_run_command_error(mock_stdout_write, mock_stderr_write, mock_lab, mock_parse_lab, mock_docker_manager,
                           mock_manager_get_instance):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec_link.side_effect = LinkCommandError("A", "vlan/create 10", 1017, "File exists")
    command = SwitchCommand()
    exit_code = command.run('.', ['A', 'vlan/create', '10'])
    assert exit_code == 1
    mock_stderr_write.assert_called_once_with("1017 File exists\n")
    assert not mock_stdout_write.called


@mock.patch("builtins.input")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stderr.write')
@mock.patch('sys.stdout.write')
def test_run_interactive(mock_stdout_write, mock_stderr_write, mock_lab, mock_parse_lab, mock_docker_manager,
                         mock_manager_get_instance, mock_input):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.exec_link.side_effect = [
        "VLAN 0010", LinkCommandError("A", "vlan/create 10", 1017, "File exists"), ""
    ]
    mock_input.side_effect = ["vlan/print", "", "  vlan/create 10 ", "vlan/create 20", "exit", "vlan/print 20"]
    command = SwitchCommand()
    exit_code = command.run('.', ['A'])
    assert exit_code == 0
    # The collision domain is checked before the first prompt
    mock_docker_manager.get_link_ports.assert_called_once_with("A", lab_hash=mock_lab.hash)
    mock_input.assert_called_with("A$ ")
    assert mock_input.call_count == 5
    assert mock_docker_manager.exec_link.call_args_list == [
        mock.call("A", "vlan/print", lab_hash=mock_lab.hash),
        mock.call("A", "vlan/create 10", lab_hash=mock_lab.hash),
        mock.call("A", "vlan/create 20", lab_hash=mock_lab.hash),
    ]
    mock_stdout_write.assert_called_once_with("VLAN 0010\n")
    mock_stderr_write.assert_called_once_with("1017 File exists\n")


@mock.patch("builtins.input")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
@mock.patch('sys.stdout.write')
def test_run_interactive_end_of_input(mock_stdout_write, mock_lab, mock_parse_lab, mock_docker_manager,
                                      mock_manager_get_instance, mock_input):
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_input.side_effect = EOFError
    command = SwitchCommand()
    exit_code = command.run('.', ['A'])
    assert exit_code == 0
    assert not mock_docker_manager.exec_link.called
    mock_stdout_write.assert_called_once_with("\n")
