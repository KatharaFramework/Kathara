import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.ListCommand import ListCommand
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import PrivilegeError


@pytest.fixture()
def test_lab():
    lab = Lab('test_lab')
    lab.get_or_new_machine('pc1')
    lab.connect_machine_to_link(machine_name='pc1', link_name='A')
    lab.connect_machine_to_link(machine_name='pc1', link_name='B')
    return lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_no_params(mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = ListCommand()
    command.run('.', [])
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name=None, all_users=False)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.utils.is_admin")
def test_run_all(mock_is_admin, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_is_admin.return_value = True
    command = ListCommand()
    command.run('.', ['-a'])
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name=None, all_users=True)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.utils.is_admin")
def test_run_all_name(mock_is_admin, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_is_admin.return_value = True
    command = ListCommand()
    command.run('.', ['-a', '-n', 'pc1'])
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name='pc1', all_users=True)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.utils.is_admin")
def test_run_all_no_root(mock_is_admin, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_is_admin.return_value = False
    command = ListCommand()
    with pytest.raises(PrivilegeError):
        command.run('.', ['-a'])
    assert not mock_docker_manager.get_machines_stats.called


@mock.patch("src.Kathara.cli.command.ListCommand.ListCommand._get_live_info")
@mock.patch("src.Kathara.utils.is_admin")
def test_run_all_watch(mock_is_admin, mock_get_live_info, test_lab):
    mock_is_admin.return_value = True
    command = ListCommand()
    command.run('.', ['-a', '-w'])
    mock_get_live_info.assert_called_once_with(machine_name=None, all_users=True)


@mock.patch("src.Kathara.cli.command.ListCommand.ListCommand._get_live_info")
@mock.patch("src.Kathara.utils.is_admin")
def test_run_all_watch_name(mock_is_admin, mock_get_live_info, test_lab):
    mock_is_admin.return_value = True
    command = ListCommand()
    command.run('.', ['-a', '-w', '-n', 'pc1'])
    mock_get_live_info.assert_called_once_with(machine_name='pc1', all_users=True)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_name(mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = ListCommand()
    command.run('.', ['-n', 'pc1'])
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name='pc1', all_users=False)


@mock.patch("rich.live.Live.update", side_effect=[None, KeyboardInterrupt])
@mock.patch("src.Kathara.cli.command.ListCommand.create_lab_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_get_live_info_machine_name(mock_docker_manager, mock_manager_get_instance, mock_create_lab_table, mock_update,
                                    test_lab):
    stats = map(lambda x: x, [])
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_docker_manager.get_machines_stats.return_value = stats
    with pytest.raises(KeyboardInterrupt):
        ListCommand()._get_live_info('pc1', False)
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name='pc1', all_users=False)
    mock_create_lab_table.assert_called_once_with(stats)
    assert mock_update.call_count == 2


@mock.patch("rich.live.Live.update", side_effect=[None, KeyboardInterrupt])
@mock.patch("src.Kathara.cli.command.ListCommand.create_lab_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_get_live_info(mock_docker_manager, mock_manager_get_instance, mock_create_lab_table, mock_update):
    mock_manager_get_instance.return_value = mock_docker_manager
    stats = map(lambda x: x, [])
    mock_docker_manager.get_machines_stats.return_value = stats
    with pytest.raises(KeyboardInterrupt):
        ListCommand()._get_live_info(None, False)
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name=None, all_users=False)
    mock_create_lab_table.assert_called_once_with(stats)
    assert mock_update.call_count == 2


@mock.patch("rich.live.Live.update", side_effect=[None, KeyboardInterrupt])
@mock.patch("src.Kathara.cli.command.ListCommand.create_lab_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_get_live_info_all_users(mock_docker_manager, mock_manager_get_instance, mock_create_lab_table, mock_update):
    mock_manager_get_instance.return_value = mock_docker_manager
    stats = map(lambda x: x, [])
    mock_docker_manager.get_machines_stats.return_value = stats
    with pytest.raises(KeyboardInterrupt):
        ListCommand()._get_live_info(None, True)
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name=None, all_users=True)
    mock_create_lab_table.assert_called_once_with(stats)
    assert mock_update.call_count == 2


@mock.patch("rich.live.Live.update", side_effect=[None, KeyboardInterrupt])
@mock.patch("src.Kathara.cli.command.ListCommand.create_lab_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_get_live_info_machine_name_all_users(mock_docker_manager, mock_manager_get_instance, mock_create_lab_table,
                                              mock_update):
    mock_manager_get_instance.return_value = mock_docker_manager
    stats = map(lambda x: x, [])
    mock_docker_manager.get_machines_stats.return_value = stats
    with pytest.raises(KeyboardInterrupt):
        ListCommand()._get_live_info('pc1', True)
    mock_docker_manager.get_machines_stats.assert_called_once_with(machine_name='pc1', all_users=True)
    mock_create_lab_table.assert_called_once_with(stats)
    assert mock_update.call_count == 2
