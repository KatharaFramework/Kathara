import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.LconfigCommand import LconfigCommand
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Link import Link
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import MachineNotFoundError


@pytest.fixture()
def test_lab():
    lab = Lab('test_lab')
    device = Machine(lab, 'pc1')
    link_a = Link(lab, "A")
    link_b = Link(lab, "B")
    lab.machines['pc1'] = device
    lab.links = {'A': link_a, 'B': link_b}
    return lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    test_lab.connect_machine_to_link("pc1", "A")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-n', 'pc1', '--add', 'A'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.connect_machine_to_link.assert_called_once_with(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[0].link,
        mac_address=None
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface_with_mac_address(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    test_lab.connect_machine_to_link("pc1", "A")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-n', 'pc1', '--add', 'A/00:00:00:00:00:01'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.connect_machine_to_link.assert_called_once_with(
        test_lab.get_machine('pc1'),
        test_lab.get_machine('pc1').interfaces[0].link,
        mac_address='00:00:00:00:00:01'
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface_invalid_interface_definition(mock_parse_lab, mock_docker_manager, mock_manager_get_instance,
                                                        test_lab):
    test_lab.connect_machine_to_link("pc1", "A")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    with pytest.raises(SyntaxError):
        command.run('.', ['-n', 'pc1', '--add', 'B/00:/00:00:00:00:01'])


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface_with_directory(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    test_lab.connect_machine_to_link("pc1", "A")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-d', os.path.join('/test', 'path'), '-n', 'pc1', '--add', 'A'])
    mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.connect_machine_to_link.assert_called_once_with(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[0].link,
        mac_address=None
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_two_interfaces(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    test_lab.connect_machine_to_link("pc1", "A")
    test_lab.connect_machine_to_link("pc1", "B")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-n', 'pc1', '--add', 'A', 'B'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.connect_machine_to_link.assert_any_call(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[0].link,
        mac_address=None
    )
    mock_docker_manager.connect_machine_to_link.assert_any_call(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[1].link,
        mac_address=None
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_two_interfaces_one_mac_address(mock_parse_lab, mock_docker_manager, mock_manager_get_instance,
                                                test_lab):
    test_lab.connect_machine_to_link("pc1", "A")
    test_lab.connect_machine_to_link("pc1", "B")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-n', 'pc1', '--add', 'A', 'B/00:00:00:00:00:01'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.connect_machine_to_link.assert_any_call(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[0].link,
        mac_address=None
    )
    mock_docker_manager.connect_machine_to_link.assert_any_call(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[1].link,
        mac_address='00:00:00:00:00:01'
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface_with_directory(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    test_lab.connect_machine_to_link("pc1", "A")

    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-d', os.path.join('/test', 'path'), '-n', 'pc1', '--add', 'A'])
    mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.connect_machine_to_link.assert_called_once_with(
        test_lab.get_machine('pc1'),
        test_lab.get_machine("pc1").interfaces[0].link,
        mac_address=None
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_remove_interface(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-n', 'pc1', '--rm', 'A'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.disconnect_machine_from_link.assert_called_once_with(test_lab.get_or_new_machine('pc1'),
                                                                             test_lab.get_or_new_link('A'))


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_remove_interface_with_directory_absolute_path(mock_parse_lab, mock_docker_manager,
                                                           mock_manager_get_instance,
                                                           test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-d', os.path.join('/test', 'path'), '-n', 'pc1', '--rm', 'A'])
    mock_parse_lab.assert_called_once_with(os.path.abspath(os.path.join('/test', 'path')))
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.disconnect_machine_from_link.assert_called_once_with(test_lab.get_or_new_machine('pc1'),
                                                                             test_lab.get_or_new_link('A'))


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_remove_interface_with_directory_relative_path(mock_parse_lab, mock_docker_manager,
                                                           mock_manager_get_instance,
                                                           test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-d', os.path.join('test', 'path'), '-n', 'pc1', '--rm', 'A'])
    mock_parse_lab.assert_called_once_with(os.path.join(os.getcwd(), 'test', 'path'))
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.disconnect_machine_from_link.assert_called_once_with(test_lab.get_or_new_machine('pc1'),
                                                                             test_lab.get_or_new_link('A'))


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_remove_two_interfaces(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    command.run('.', ['-n', 'pc1', '--rm', 'A', 'B'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)
    mock_docker_manager.disconnect_machine_from_link.assert_any_call(test_lab.get_or_new_machine('pc1'),
                                                                     test_lab.get_or_new_link('A'))
    mock_docker_manager.disconnect_machine_from_link.assert_any_call(test_lab.get_or_new_machine('pc1'),
                                                                     test_lab.get_or_new_link('B'))


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_machine_not_found_error(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = LconfigCommand()
    with pytest.raises(MachineNotFoundError):
        command.run('.', ['-n', 'pc10', '--add', 'A'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.update_lab_from_api.assert_called_once_with(test_lab)


def test_run_system_exit_error():
    command = LconfigCommand()
    with pytest.raises(SystemExit):
        command.run('.', ['-n', 'pc1', '--rm', 'A', '--add', 'A'])
