import os
import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.RestoreCommand import RestoreCommand


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_relative_path(mock_docker_manager, mock_manager_get_instance):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = RestoreCommand()
    command.run('.', ['my.tar'])
    mock_docker_manager.restore_lab.assert_called_once_with(os.path.join(os.getcwd(), 'my.tar'))


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_absolute_path(mock_docker_manager, mock_manager_get_instance):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = RestoreCommand()
    command.run('.', [os.path.join('/saves', 'my.tar')])
    mock_docker_manager.restore_lab.assert_called_once_with(os.path.join('/saves', 'my.tar'))


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_noterminals(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting = mock_setting_get_instance.return_value
    command = RestoreCommand()
    command.run('.', ['--noterminals', 'my.tar'])
    assert mock_setting.open_terminals is False
    mock_docker_manager.restore_lab.assert_called_once_with(os.path.join(os.getcwd(), 'my.tar'))


@mock.patch("src.Kathara.cli.command.RestoreCommand.create_lab_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_list(mock_docker_manager, mock_manager_get_instance, mock_create_lab_table):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = RestoreCommand()
    command.run('.', ['-l', 'my.tar'])
    mock_docker_manager.restore_lab.assert_called_once_with(os.path.join(os.getcwd(), 'my.tar'))
    mock_docker_manager.get_machines_stats.assert_called_once_with(
        lab_hash=mock_docker_manager.restore_lab.return_value.hash
    )
    mock_create_lab_table.assert_called_once()
