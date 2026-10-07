import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.LconfigCommand import LconfigCommand
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Link import Link
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import MachineNotFoundError, NotSupportedError, LinkNotFoundError


@pytest.fixture()
def test_lab():
    lab = Lab('test_lab')
    device = Machine(lab, 'pc1')
    link_a = Link(lab, "A")
    link_b = Link(lab, "B")
    lab.machines['pc1'] = device
    lab.links = {'A': link_a, 'B': link_b}
    return lab


@pytest.fixture()
def docker_manager():
    from src.Kathara.manager.docker.DockerManager import DockerManager
    with mock.patch("docker.from_env"), mock.patch("src.Kathara.manager.docker.DockerLink.DockerPlugin"):
        manager = DockerManager()

    # The network scenario is already the running one
    with mock.patch.object(DockerManager, "update_lab_from_api"):
        yield manager


@pytest.fixture()
def p2p_lab():
    lab = Lab('test_lab')
    lab.connect_machine_to_link('pc1', 'A')
    lab.connect_machine_to_link('pc2', 'A')
    lab.get_or_new_machine('pc3')
    lab.get_or_new_link('B')
    for device in lab.machines.values():
        device.api_object = mock.Mock(status="running")
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


@mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_assigns_link_types_before_updating_from_api(mock_parse_lab, mock_docker_manager,
                                                         mock_manager_get_instance, mock_parse_link, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_parse_link.return_value = ({'A': 'p2p', 'B': 'hub'}, {})
    mock_manager_get_instance.return_value = mock_docker_manager

    # The types must already be assigned when the running network scenario is loaded
    types_when_updated = {}
    mock_docker_manager.update_lab_from_api.side_effect = \
        lambda lab: types_when_updated.update({name: link.type for name, link in lab.links.items()})

    LconfigCommand().run('.', ['-n', 'pc1', '--add', 'B'])

    mock_parse_link.assert_called_once_with(os.getcwd())
    assert types_when_updated == {'A': 'p2p', 'B': 'hub'}
    mock_docker_manager.connect_machine_to_link.assert_called_once_with(
        test_lab.get_machine('pc1'), test_lab.get_link('B'), mac_address=None
    )


@mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_without_lab_link(mock_parse_lab, mock_docker_manager, mock_manager_get_instance, mock_parse_link,
                              test_lab):
    mock_parse_lab.return_value = test_lab
    mock_parse_link.side_effect = FileNotFoundError
    mock_manager_get_instance.return_value = mock_docker_manager

    LconfigCommand().run('.', ['-n', 'pc1', '--add', 'A'])

    assert all(link.type is None for link in test_lab.links.values())
    mock_docker_manager.connect_machine_to_link.assert_called_once()


@mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_lab_link_unknown_collision_domain(mock_parse_lab, mock_docker_manager, mock_manager_get_instance,
                                               mock_parse_link, test_lab):
    mock_parse_lab.return_value = test_lab
    mock_parse_link.return_value = ({'Z': 'p2p'}, {})
    mock_manager_get_instance.return_value = mock_docker_manager

    with pytest.raises(LinkNotFoundError):
        LconfigCommand().run('.', ['-n', 'pc1', '--add', 'A'])

    assert not mock_docker_manager.update_lab_from_api.called
    assert not mock_docker_manager.connect_machine_to_link.called


@mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface_p2p_link(mock_parse_lab, mock_manager_get_instance, mock_parse_link, docker_manager,
                                    p2p_lab):
    mock_parse_lab.return_value = p2p_lab
    mock_parse_link.return_value = ({'A': 'p2p'}, {})
    mock_manager_get_instance.return_value = docker_manager

    with mock.patch(
            "src.Kathara.manager.docker.DockerMachine.DockerMachine.connect_interface") as mock_connect_interface:
        with pytest.raises(NotSupportedError, match="at runtime"):
            LconfigCommand().run('.', ['-n', 'pc3', '--add', 'A'])

    assert not mock_connect_interface.called
    assert set(p2p_lab.get_link('A').machines.keys()) == {'pc1', 'pc2'}
    assert len(p2p_lab.get_machine('pc3').interfaces) == 0


@mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_remove_interface_p2p_link(mock_parse_lab, mock_manager_get_instance, mock_parse_link, docker_manager,
                                       p2p_lab):
    mock_parse_lab.return_value = p2p_lab
    mock_parse_link.return_value = ({'A': 'p2p'}, {})
    mock_manager_get_instance.return_value = docker_manager

    with mock.patch(
            "src.Kathara.manager.docker.DockerMachine.DockerMachine.disconnect_from_link") as mock_disconnect_from_link:
        with pytest.raises(NotSupportedError, match="at runtime"):
            LconfigCommand().run('.', ['-n', 'pc1', '--rm', 'A'])

    assert not mock_disconnect_from_link.called
    assert set(p2p_lab.get_link('A').machines.keys()) == {'pc1', 'pc2'}


@mock.patch("src.Kathara.parser.netkit.LinkParser.LinkParser.parse")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_add_interface_not_p2p_link_with_lab_link(mock_parse_lab, mock_manager_get_instance, mock_parse_link,
                                                      docker_manager, p2p_lab):
    mock_parse_lab.return_value = p2p_lab
    mock_parse_link.return_value = ({'A': 'p2p', 'B': 'hub'}, {})
    mock_manager_get_instance.return_value = docker_manager

    with mock.patch(
            "src.Kathara.manager.docker.DockerMachine.DockerMachine.connect_interface") as mock_connect_interface, \
            mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.deploy_link") as mock_deploy_link:
        LconfigCommand().run('.', ['-n', 'pc3', '--add', 'B'])

    mock_deploy_link.assert_called_once_with(p2p_lab.get_link('B'))
    mock_connect_interface.assert_called_once()
    assert 'pc3' in p2p_lab.get_link('B').machines
