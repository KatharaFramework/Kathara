import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.LstartCommand import LstartCommand
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import PrivilegeError


@pytest.fixture()
def test_lab():
    lab = Lab("test_lab")
    lab.get_or_new_machine('pc1')
    lab.connect_machine_to_link(machine_name='pc1', link_name='A')
    lab.connect_machine_to_link(machine_name='pc1', link_name='B')
    return lab


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting")
def mock_setting(mock_setting_class):
    setting = mock_setting_class()
    setting.configure_mock(**{
        'open_terminals': True,
        'terminal': '/usr/bin/xterm',
    })
    return setting


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_no_params(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                       mock_manager_get_instance, test_lab, mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', [])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_directory_absolute_path(mock_setting_get_instance, mock_parse_lab, mock_parse_dep,
                                          mock_docker_manager, mock_manager_get_instance,
                                          test_lab, mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-d', os.path.join('/test', 'path')])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
        mock_parse_dep.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_directory_relative_path(mock_setting_get_instance, mock_parse_lab, mock_parse_dep,
                                          mock_docker_manager, mock_manager_get_instance,
                                          test_lab, mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-d', os.path.join('test', 'path')])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), 'test', 'path'))
        mock_parse_dep.assert_called_once_with(os.path.join(os.getcwd(), 'test', 'path'))
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_no_terminals(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                               mock_manager_get_instance, test_lab,
                               mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--noterminals'])
        assert not mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_terminals(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                            mock_manager_get_instance, test_lab,
                            mock_setting):
    mock_setting.open_terminals = False
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--terminals'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_privileged(mock_setting_get_instance, mock_is_admin, mock_parse_lab, mock_parse_dep,
                             mock_docker_manager, mock_manager_get_instance,
                             test_lab,
                             mock_setting):
    mock_is_admin.return_value = True
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--privileged'])
        assert not mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', True)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_privileged_no_root(mock_setting_get_instance, mock_is_admin, mock_parse_lab, mock_parse_dep,
                                     mock_docker_manager, mock_manager_get_instance, test_lab,
                                     mock_setting):
    mock_is_admin.return_value = False
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with pytest.raises(PrivilegeError):
        command.run('.', ['--privileged'])
        assert not mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert not mock_parse_lab.called
        assert not mock_parse_dep.called
        assert not mock_docker_manager.deploy_lab.called


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.FolderParser.FolderParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse", side_effect=IOError)
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_force_lab(mock_setting_get_instance, mock_parse_lab, mock_parse_folder, mock_parse_dep,
                            mock_docker_manager, mock_manager_get_instance, test_lab, mock_setting):
    mock_parse_folder.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-F'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_folder.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.cli.command.LstartCommand.create_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_list(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                       mock_manager_get_instance, mock_create_table, test_lab, mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    stats = map(lambda x: x, [])
    mock_docker_manager.get_machines_stats.return_value = stats
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-l'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())
        mock_docker_manager.get_machines_stats.assert_called_once_with(lab_hash=test_lab.hash)
        mock_create_table.assert_called_once_with(stats)


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_one_general_option(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                                     mock_manager_get_instance,
                                     test_lab,
                                     mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-o', 'mem=64M'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        assert test_lab.general_options == {'mem': '64M'}
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_two_general_option(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                                     mock_manager_get_instance,
                                     test_lab,
                                     mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-o', 'mem=64M', 'cpu=100'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        assert test_lab.general_options == {'mem': '64M', 'cpu': '100'}
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_xterm(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                        mock_manager_get_instance, test_lab,
                        mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--xterm', 'terminal'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == 'terminal'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_dry_mode(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                           mock_manager_get_instance, test_lab,
                           mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        with pytest.raises(SystemExit):
            command.run('.', ['--dry-mode'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            assert not mock_add_option.called
            assert not mock_docker_manager.deploy_lab.called


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_no_hosthome(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                              mock_manager_get_instance, test_lab,
                              mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--no-hosthome'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', False)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_hosthome(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                           mock_manager_get_instance, test_lab,
                           mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--hosthome'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', True)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_shared(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                         mock_manager_get_instance, test_lab,
                         mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--shared'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', True)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_no_shared(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                            mock_manager_get_instance, test_lab,
                            mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['--no-shared'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines=set())


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_one_device(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                             mock_manager_get_instance, test_lab,
                             mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['pc1'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines={'pc1'})


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_two_device(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                             mock_manager_get_instance, test_lab,
                             mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['pc1', 'pc2'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', None)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_docker_manager.deploy_lab.assert_called_once_with(test_lab, selected_machines={'pc1', 'pc2'})
