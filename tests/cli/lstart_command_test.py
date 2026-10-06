import logging
import os
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.LstartCommand import LstartCommand
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import PrivilegeError, LinkNotFoundError
from src.Kathara.model.ExternalLink import ExternalLink


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


@pytest.fixture()
def lstart_env(test_lab, mock_setting):
    """Patches everything lstart needs; lab.link and lab.ext are absent unless a test sets their return values."""
    with mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance") as mock_manager_get_instance, \
            mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse", return_value=None), \
            mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse", return_value=test_lab), \
            mock.patch("src.Kathara.setting.Setting.Setting.get_instance", return_value=mock_setting), \
            mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse",
                       side_effect=FileNotFoundError) as mock_parse_link, \
            mock.patch("src.Kathara.parser.netkit.ExtParser.ExtParser.parse",
                       side_effect=FileNotFoundError) as mock_parse_ext, \
            mock.patch("src.Kathara.utils.is_admin", return_value=True) as mock_is_admin, \
            mock.patch("src.Kathara.utils.is_platform", return_value=True) as mock_is_platform:
        manager = mock.MagicMock()
        mock_manager_get_instance.return_value = manager

        yield SimpleNamespace(
            lab=test_lab, manager=manager, parse_link=mock_parse_link, parse_ext=mock_parse_ext,
            is_admin=mock_is_admin, is_platform=mock_is_platform
        )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', [])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['-d', os.path.join('/test', 'path')])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
            mock_parse_dep.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['-d', os.path.join('test', 'path')])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), 'test', 'path'))
            mock_parse_dep.assert_called_once_with(os.path.join(os.getcwd(), 'test', 'path'))
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--noterminals'])
            assert not mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--terminals'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--privileged'])
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', True)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_one_machine_privileged(mock_setting_get_instance, mock_is_admin, mock_parse_lab, mock_parse_dep,
                                         mock_docker_manager, mock_manager_get_instance, test_lab, mock_setting):
    pc1 = test_lab.get_machine('pc1')
    pc1.add_meta('privileged', True)

    mock_is_admin.return_value = True
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', [])
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_one_machine_privileged_no_root(mock_setting_get_instance, mock_is_admin, mock_parse_lab,
                                                 mock_parse_dep, mock_docker_manager, mock_manager_get_instance,
                                                 test_lab, mock_setting):
    pc1 = test_lab.get_machine('pc1')
    pc1.add_meta('privileged', True)

    mock_is_admin.return_value = False
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with pytest.raises(PrivilegeError):
        command.run('.', [])
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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['-F'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_folder.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


@mock.patch("src.Kathara.cli.command.LstartCommand.create_lab_table")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_list(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                       mock_manager_get_instance, mock_create_lab_table, test_lab, mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    stats = map(lambda x: x, [])
    mock_docker_manager.get_machines_stats.return_value = stats
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['-l'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )
            mock_docker_manager.get_machines_stats.assert_called_once_with(lab_hash=test_lab.hash)
            mock_create_lab_table.assert_called_once_with(stats)


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['-o', 'mem=64M'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            assert test_lab.global_machine_metadata == {'mem': '64M'}
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['-o', 'mem=64M', 'cpu=100'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            assert test_lab.global_machine_metadata == {'mem': '64M', 'cpu': '100'}
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_terminal_emu(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                               mock_manager_get_instance, test_lab,
                               mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--terminal-emu', 'terminal'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == 'terminal'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        code = command.run('.', ['--dry-mode'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        mock_parse_lab.assert_called_once_with(os.getcwd())
        mock_parse_dep.assert_called_once_with(os.getcwd())
        assert not mock_add_option.called
        assert not mock_docker_manager.deploy_lab.called
        assert code == 0


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--no-hosthome'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', False)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--hosthome'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', True)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--shared'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', True)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--no-shared'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', False)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['pc1'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines={'pc1'}, excluded_machines=set()
            )


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
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['pc1', 'pc2'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines={'pc1', 'pc2'}, excluded_machines=set()
            )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_exclude_one_device(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                                mock_manager_get_instance, test_lab,
                                mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--exclude', 'pc1'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines={'pc1'}
            )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.DepParser.DepParser.parse")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_exclude_two_device(mock_setting_get_instance, mock_parse_lab, mock_parse_dep, mock_docker_manager,
                                mock_manager_get_instance, test_lab,
                                mock_setting):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = LstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        with mock.patch.object(Lab, "add_global_machine_metadata") as mock_add_global_machine_metadata:
            command.run('.', ['--exclude', 'pc1', 'pc2'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            mock_parse_lab.assert_called_once_with(os.getcwd())
            mock_parse_dep.assert_called_once_with(os.getcwd())
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', None)
            mock_add_global_machine_metadata.assert_any_call('privileged', None)
            mock_docker_manager.deploy_lab.assert_called_once_with(
                test_lab, selected_machines=set(), excluded_machines={'pc1', 'pc2'}
            )


def test_run_no_link_no_ext(lstart_env):
    LstartCommand().run('.', [])

    lstart_env.parse_link.assert_called_once_with(os.getcwd())
    lstart_env.parse_ext.assert_called_once_with(os.getcwd())
    assert all(link.type is None for link in lstart_env.lab.links.values())
    assert all(not link.external for link in lstart_env.lab.links.values())
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_link_types(lstart_env):
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({'A': 'bridge', 'B': 'hub'}, {})

    LstartCommand().run('.', [])

    assert lstart_env.lab.links['A'].type == 'bridge'
    assert lstart_env.lab.links['B'].type == 'hub'
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_link_types_link_not_found(lstart_env):
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({'Z': 'p2p'}, {})

    with pytest.raises(LinkNotFoundError):
        LstartCommand().run('.', [])

    assert not lstart_env.manager.deploy_lab.called


def test_run_link_types_only_does_not_require_root_or_linux(lstart_env):
    lstart_env.is_admin.return_value = False
    lstart_env.is_platform.return_value = False
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({'A': 'hub'}, {})

    LstartCommand().run('.', [])

    assert lstart_env.lab.links['A'].type == 'hub'
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_link_external_links(lstart_env):
    external_link = ExternalLink('eth0')
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({}, {'A': [external_link]})

    LstartCommand().run('.', [])

    assert lstart_env.lab.links['A'].external == [external_link]
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_ext_external_links(lstart_env):
    external_link = ExternalLink('eth0', 30)
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = {'A': [external_link]}

    LstartCommand().run('.', [])

    assert lstart_env.lab.links['A'].external == [external_link]
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_ext_empty_file(lstart_env):
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = None

    LstartCommand().run('.', [])

    assert all(not link.external for link in lstart_env.lab.links.values())
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_ext_deprecation_warning(lstart_env, caplog):
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = {'A': [ExternalLink('eth0')]}

    with caplog.at_level(logging.WARNING):
        LstartCommand().run('.', [])

    assert "`lab.ext` is deprecated" in caplog.text


def test_run_no_ext_no_deprecation_warning(lstart_env, caplog):
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({}, {'A': [ExternalLink('eth0')]})

    with caplog.at_level(logging.WARNING):
        LstartCommand().run('.', [])

    assert "deprecated" not in caplog.text


def test_run_link_and_ext_different_collision_domains(lstart_env):
    link_external = ExternalLink('eth0')
    ext_external = ExternalLink('eth1', 20)
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({'A': 'hub'}, {'A': [link_external]})
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = {'B': [ext_external]}

    LstartCommand().run('.', [])

    assert lstart_env.lab.links['A'].external == [link_external]
    assert lstart_env.lab.links['B'].external == [ext_external]
    lstart_env.manager.deploy_lab.assert_called_once()


def test_run_same_collision_domain_in_link_and_ext(lstart_env):
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({}, {'A': [ExternalLink('eth0')], 'B': [ExternalLink('eth0')]})
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = {'A': [ExternalLink('eth1')], 'B': [ExternalLink('eth1')]}

    with pytest.raises(ValueError) as e:
        LstartCommand().run('.', [])

    assert "`A`" in str(e.value) and "`B`" in str(e.value)
    assert "`lab.link` and `lab.ext`" in str(e.value)
    assert all(not link.external for link in lstart_env.lab.links.values())
    assert not lstart_env.manager.deploy_lab.called


def test_run_external_links_no_root(lstart_env):
    lstart_env.is_admin.return_value = False
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({}, {'A': [ExternalLink('eth0')]})

    with pytest.raises(PrivilegeError):
        LstartCommand().run('.', [])

    assert not lstart_env.manager.deploy_lab.called


def test_run_ext_links_no_root(lstart_env):
    lstart_env.is_admin.return_value = False
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = {'A': [ExternalLink('eth0')]}

    with pytest.raises(PrivilegeError):
        LstartCommand().run('.', [])

    assert not lstart_env.manager.deploy_lab.called


def test_run_external_links_not_linux(lstart_env):
    lstart_env.is_platform.return_value = False
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({}, {'A': [ExternalLink('eth0')]})

    with pytest.raises(OSError):
        LstartCommand().run('.', [])

    assert not lstart_env.manager.deploy_lab.called


def test_run_external_links_collision_domain_not_found(lstart_env):
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({}, {'Z': [ExternalLink('eth0')]})

    with pytest.raises(LinkNotFoundError):
        LstartCommand().run('.', [])

    assert not lstart_env.manager.deploy_lab.called


def test_run_dry_mode_with_link_and_ext(lstart_env, capsys):
    lstart_env.parse_link.side_effect = None
    lstart_env.parse_link.return_value = ({'A': 'hub'}, {})
    lstart_env.parse_ext.side_effect = None
    lstart_env.parse_ext.return_value = {'B': [ExternalLink('eth0')]}

    assert LstartCommand().run('.', ['--dry-mode']) == 0

    out = capsys.readouterr().out
    assert "lab.link" in out
    assert "lab.ext" in out
    assert not lstart_env.manager.deploy_lab.called


def test_run_p2p_link(lstart_env):
    lab = Lab("p2p_lab")
    lab.connect_machine_to_link('pc1', 'A')
    lab.connect_machine_to_link('pc2', 'A')
    with mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse", return_value=lab):
        lstart_env.parse_link.side_effect = None
        lstart_env.parse_link.return_value = ({'A': 'p2p'}, {})

        LstartCommand().run('.', [])

    assert lab.links['A'].type == 'p2p'
    # The constraints of the collision domains are checked by the manager when deploying the lab
    lstart_env.manager.deploy_lab.assert_called_once()
