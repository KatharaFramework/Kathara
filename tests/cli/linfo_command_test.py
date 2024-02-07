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
    command.run('.', ['-d', os.path.join('/test' 'path')])
    mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test' 'path')))
    mock_docker_manager.get_machines_stats.assert_called_once_with(test_lab.hash)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_directory_relative_path(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LinfoCommand()
    command.run('.', ['-d', os.path.join('test', 'path')])
    mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), os.path.join('test', 'path')))
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


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("rich.live.Live.update", side_effect=[None, KeyboardInterrupt])
def test_get_machine_live_info(mock_update, mock_docker_manager, mock_manager_get_instance,
                               test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LinfoCommand()
    with pytest.raises(KeyboardInterrupt):
        command._get_machine_live_info(test_lab, 'pc1')
    mock_docker_manager.get_machine_stats.assert_called_once_with('pc1', test_lab.hash)
    assert mock_update.call_count == 2


@mock.patch("src.Kathara.cli.command.LinfoCommand.create_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("rich.live.Live.update", side_effect=[None, KeyboardInterrupt])

def test_get_lab_live_info(mock_update, mock_docker_manager, mock_manager_get_instance, mock_create_table,
                           test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    machine_stats = map(lambda x: x, [{"A": MagicMock()}])
    mock_docker_manager.get_machines_stats.return_value = machine_stats
    with pytest.raises(KeyboardInterrupt):
        LinfoCommand()._get_lab_live_info(test_lab)
    mock_docker_manager.get_machines_stats.assert_called_once_with(test_lab.hash)
    assert mock_update.call_count == 2
