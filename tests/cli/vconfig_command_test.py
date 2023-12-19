import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.VconfigCommand import VconfigCommand
from src.Kathara.model.Lab import Lab


@mock.patch("src.Kathara.model.Lab.Lab.get_machine")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_add_link(mock_docker_manager, mock_manager_get_instance, mock_get_machine):
    lab = Lab('kathara_vlab')
    pc1 = lab.new_machine("pc1")
    mock_get_machine.return_value = pc1
    mock_manager_get_instance.return_value = mock_docker_manager
    command = VconfigCommand()
    command.run('.', ['-n', 'pc1', '--add', 'A'])
    mock_docker_manager.get_machine_api_object.assert_called_once_with('pc1', lab_name='kathara_vlab')
    mock_docker_manager.connect_machine_to_link.assert_called_once()


@mock.patch("src.Kathara.model.Lab.Lab.get_machine")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_remove_link(mock_docker_manager, mock_manager_get_instance, mock_get_machine):
    lab = Lab('kathara_vlab')
    pc1 = lab.new_machine("pc1")
    lab.new_link("A")
    mock_get_machine.return_value = pc1
    mock_manager_get_instance.return_value = mock_docker_manager
    command = VconfigCommand()
    command.run('.', ['-n', 'pc1', '--rm', 'A'])
    mock_docker_manager.get_machine_api_object.assert_called_once_with('pc1', lab_name='kathara_vlab')
    mock_docker_manager.get_link_api_object.assert_called_once_with('A', lab_name='kathara_vlab')
    mock_docker_manager.disconnect_machine_from_link.assert_called_once()
