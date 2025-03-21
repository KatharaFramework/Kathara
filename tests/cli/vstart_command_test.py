import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.VstartCommand import VstartCommand
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.exceptions import PrivilegeError


@pytest.fixture()
def test_lab():
    lab = Lab("kathara_vlab")
    return lab


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting")
def mock_setting(mock_setting_class):
    setting = mock_setting_class()
    setting.configure_mock(**{
        'open_terminals': True,
        'terminal': '/usr/bin/xterm',
        'device_shell': '/usr/bin/bash'
    })
    return setting


@pytest.fixture()
def default_device_args():
    args = {
        "terminals": None, "privileged": None, "num_terms": None, "eths": None, "exec_commands": None, "mem": None,
        "cpus": None, "image": None, "hosthome_mount": None, "xterm": None, "dry_mode": False, "bridged": False,
        "ports": None, "sysctls": None, "envs": None, "ulimits": None, "shell": None
    }
    return args


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_no_params(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                       mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                       default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_no_terminals(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                               mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                               mock_setting, default_device_args):
    mock_setting_get_instance.return_value = mock_setting
    mock_manager_get_instance.return_value = mock_docker_manager
    default_device_args['terminals'] = False
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--noterminals'])
        assert not mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_terminals(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                            mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                            default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting.open_terminals = False
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['terminals'] = True
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--terminals'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_privileged(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance, mock_is_admin,
                             mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                             mock_setting, default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    mock_is_admin.return_value = True
    default_device_args['privileged'] = True
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--privileged'])
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', True)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_privileged_no_root(mock_setting_get_instance, mock_is_admin,
                                     test_lab, mock_setting, default_device_args):
    mock_setting_get_instance.return_value = mock_setting
    mock_is_admin.return_value = False
    default_device_args['privileged'] = True
    command = VstartCommand()
    with pytest.raises(PrivilegeError):
        command.run('.', ['-n', 'pc1', '--privileged'])
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.manager.Kathara.Kathara.deploy_lab")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_two_terminals(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                                mock_deploy_lab, mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                                mock_setting, default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['num_terms'] = '2'
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--num_terms', '2'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_one_interface(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                                mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                                mock_setting, default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    mock_get_or_new_machine.return_value = Machine(test_lab, 'pc1')
    default_device_args['eths'] = [('0', 'A', None)]
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--eth', '0:A'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        mock_connect_machine_to_link.assert_called_once_with('pc1', 'A', machine_iface_number=0, mac_address=None)
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_one_interface_and_mac_address(mock_docker_manager, mock_manager_get_instance,
                                                mock_setting_get_instance,
                                                mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                                                mock_setting, default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    mock_get_or_new_machine.return_value = Machine(test_lab, 'pc1')
    default_device_args['eths'] = [('0', 'A', '00:00:00:00:00:01')]
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--eth', '0:A/00:00:00:00:00:01'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        mock_connect_machine_to_link.assert_called_once_with('pc1', 'A', machine_iface_number=0,
                                                             mac_address='00:00:00:00:00:01')
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_two_interfaces(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                                 mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                                 mock_setting, default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    mock_get_or_new_machine.return_value = Machine(test_lab, 'pc1')
    default_device_args['eths'] = [('0', 'A', None), ('1', 'B', None)]
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--eth', '0:A', '1:B'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        mock_connect_machine_to_link.assert_any_call('pc1', 'A', machine_iface_number=0, mac_address=None)
        mock_connect_machine_to_link.assert_any_call('pc1', 'B', machine_iface_number=1, mac_address=None)
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.manager.Kathara.Kathara.deploy_lab")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_run_with_two_interfaces_value_error(mock_setting_get_instance, mock_deploy_lab, mock_get_or_new_machine,
                                             mock_connect_machine_to_link, test_lab, mock_setting, default_device_args):
    mock_setting_get_instance.return_value = mock_setting
    mock_get_or_new_machine.return_value = Machine(test_lab, 'pc1')
    default_device_args['eths'] = [('0', 'A'), ('Z', 'B')]
    command = VstartCommand()
    with pytest.raises(SyntaxError):
        with mock.patch.object(Lab, "add_option") as mock_add_option:
            command.run('.', ['-n', 'pc1', '--eth', '0:A', 'Z:B'])
            assert mock_setting.open_terminals
            assert mock_setting.terminal == '/usr/bin/xterm'
            assert mock_setting.device_shell == '/usr/bin/bash'
            mock_add_option.assert_any_call('hosthome_mount', None)
            mock_add_option.assert_any_call('shared_mount', False)
            mock_add_option.assert_any_call('privileged_machines', None)
            mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
            mock_connect_machine_to_link.assert_any_call('pc1', 'A', machine_iface_number=0)
            mock_connect_machine_to_link.assert_any_call('pc1', 'B', machine_iface_number=1)
            assert not mock_deploy_lab.called


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_exec(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                       mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                       default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['exec_commands'] = ['echo', 'test']
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--exec', 'echo', 'test'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_mem(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                      mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                      default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['mem'] = "64M"
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--mem', '64M'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_cpus(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                       mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                       default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['cpus'] = "50"
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--cpus', '50'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_image(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                        mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                        default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['image'] = 'kathara/test'
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '-i', 'kathara/test'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_no_hosthome(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                              mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                              mock_setting, default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['hosthome_mount'] = False
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--no-hosthome'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', False)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_hosthome(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                           mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                           default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['hosthome_mount'] = True
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--hosthome'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', True)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_terminal_emu(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                               mock_get_or_new_machine, mock_connect_machine_to_link, test_lab,
                               mock_setting, default_device_args):
    mock_setting_get_instance.return_value = mock_setting
    mock_manager_get_instance.return_value = mock_docker_manager
    default_device_args['xterm'] = 'terminal'
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--terminal-emu', 'terminal'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == 'terminal'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_dry_run(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                          mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                          default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['dry_mode'] = True
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        code = command.run('.', ['-n', 'pc1', '--dry-run'])
    assert mock_setting.open_terminals
    assert mock_setting.terminal == '/usr/bin/xterm'
    assert mock_setting.device_shell == '/usr/bin/bash'
    assert not mock_add_option.called
    assert not mock_get_or_new_machine.called
    assert not mock_connect_machine_to_link.called
    assert not mock_docker_manager.deploy_lab.called
    assert code == 0


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_bridged(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                          mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                          default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['bridged'] = True
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--bridged'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_ports(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                        mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                        default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['ports'] = ['80:80/tcp']
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--port', '80:80/tcp'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_sysctl(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                         mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                         default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['sysctls'] = ['net.ip.test=True']
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--sysctl', 'net.ip.test=True'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_env(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                      mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                      default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['envs'] = ['VARIABLE=VALUE']
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--env', 'VARIABLE=VALUE'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_shell(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                        mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                        default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['shell'] = '/test/shell'
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--shell', '/test/shell'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/test/shell'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.connect_machine_to_link")
@mock.patch("src.Kathara.model.Lab.Lab.get_or_new_machine")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_ulimit(mock_docker_manager, mock_manager_get_instance, mock_setting_get_instance,
                         mock_get_or_new_machine, mock_connect_machine_to_link, test_lab, mock_setting,
                         default_device_args):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_setting_get_instance.return_value = mock_setting
    default_device_args['ulimits'] = ['testlimit=1:2', 'testlimitsoft=5']
    command = VstartCommand()
    with mock.patch.object(Lab, "add_option") as mock_add_option:
        command.run('.', ['-n', 'pc1', '--ulimit', 'testlimit=1:2', 'testlimitsoft=5'])
        assert mock_setting.open_terminals
        assert mock_setting.terminal == '/usr/bin/xterm'
        assert mock_setting.device_shell == '/usr/bin/bash'
        mock_add_option.assert_any_call('hosthome_mount', None)
        mock_add_option.assert_any_call('shared_mount', False)
        mock_add_option.assert_any_call('privileged_machines', None)
        mock_get_or_new_machine.assert_called_once_with('pc1', **default_device_args)
        assert not mock_connect_machine_to_link.called
        mock_docker_manager.deploy_lab.assert_called_once()
