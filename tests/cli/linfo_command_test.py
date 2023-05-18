import os
import sys
from unittest import mock
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.LinfoCommand import LinfoCommand
from src.Kathara.model.Lab import Lab


@pytest.fixture()
def test_lab():
    lab = Lab('test_lab')
    lab.get_or_new_machine('pc1')
    lab.connect_machine_to_link(machine_name='pc1', link_name='A')
    lab.connect_machine_to_link(machine_name='pc1', link_name='B')
    return lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_no_params(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LinfoCommand()
    command.run('.', [])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.get_machines_stats.assert_called_once_with(test_lab.hash)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_directory_absolute_path(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LinfoCommand()
    command.run('.', ['-d', '/test/path'])
    mock_parse_lab.assert_called_once_with('/test/path')
    mock_docker_manager.get_machines_stats.assert_called_once_with(test_lab.hash)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_directory_relative_path(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LinfoCommand()
    command.run('.', ['-d', 'test/path'])
    mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), 'test/path'))
    mock_docker_manager.get_machines_stats.assert_called_once_with(test_lab.hash)


@mock.patch("src.Kathara.cli.command.LinfoCommand.LinfoCommand._get_lab_live_info")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_watch(mock_parse_lab, mock_get_lab_live_info, test_lab):
    mock_parse_lab.return_value = test_lab
    command = LinfoCommand()
    command.run('.', ['-w'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_get_lab_live_info.assert_called_once_with(test_lab)


@mock.patch("src.Kathara.cli.command.LinfoCommand.LinfoCommand._get_machine_live_info")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_watch_with_name(mock_parse_lab, mock_get_machine_live_info, test_lab):
    mock_parse_lab.return_value = test_lab
    command = LinfoCommand()
    command.run('.', ['-w', '-n', 'pc1'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_get_machine_live_info.assert_called_once_with(test_lab, 'pc1')


@mock.patch("src.Kathara.cli.command.LinfoCommand.LinfoCommand._get_conf_info")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_conf(mock_parse_lab, mock_get_conf_info, test_lab):
    mock_parse_lab.return_value = test_lab
    command = LinfoCommand()
    command.run('.', ['-c'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_get_conf_info.assert_called_once_with(test_lab, machine_name=None)


@mock.patch("src.Kathara.cli.command.LinfoCommand.LinfoCommand._get_conf_info")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_conf_and_name(mock_parse_lab, mock_get_conf_info, test_lab):
    mock_parse_lab.return_value = test_lab
    command = LinfoCommand()
    command.run('.', ['-c', '-n', 'pc1'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_get_conf_info.assert_called_once_with(test_lab, machine_name='pc1')


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_name(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LinfoCommand()
    command.run('.', ['-n', 'pc1'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.get_machine_stats.assert_called_once_with('pc1', test_lab.hash)


@mock.patch("src.Kathara.trdparty.curses.curses.Curses.close")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.trdparty.curses.curses.Curses.print_string", side_effect=KeyboardInterrupt)
@mock.patch("src.Kathara.trdparty.curses.curses.Curses.init_window")
def test_get_machine_live_info(mock_init_window, mock_print_string, mock_docker_manager, mock_manager_get_instance,
                               mock_close, test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    with pytest.raises(KeyboardInterrupt):
        LinfoCommand._get_machine_live_info(test_lab, 'pc1')
    mock_init_window.assert_called_once()
    mock_print_string.assert_called_once()
    mock_docker_manager.get_machine_stats.assert_called_once_with('pc1', test_lab.hash)
    mock_close.assert_called_once()


@mock.patch("src.Kathara.trdparty.curses.curses.Curses.close")
@mock.patch("src.Kathara.trdparty.curses.curses.Curses.print_string")
@mock.patch("src.Kathara.trdparty.curses.curses.Curses.init_window")
@mock.patch("src.Kathara.cli.command.LinfoCommand.create_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_get_lab_live_info(mock_docker_manager, mock_manager_get_instance, mock_create_table, mock_init_window, mock_print_string, mock_close,
                           test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    machine_stats = map(lambda x: x, [{"A": MagicMock()}])
    mock_docker_manager.get_machines_stats.return_value = machine_stats
    mock_create_table.return_value = machine_stats
    LinfoCommand._get_lab_live_info(test_lab)
    mock_docker_manager.get_machines_stats.assert_called_once_with(test_lab.hash)
    mock_create_table.assert_called_once_with(machine_stats)
    mock_init_window.assert_called_once()
    mock_print_string.assert_called_once()
    mock_close.assert_called_once()
