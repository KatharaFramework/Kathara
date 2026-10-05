import os
import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.SaveCommand import SaveCommand


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_no_params(mock_lab, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_lab.name = "lab"
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = SaveCommand()
    command.run('.', [])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_docker_manager.save_lab.assert_called_once_with(
        os.path.join(os.getcwd(), "lab.tar"), lab=mock_lab,
        selected_machines=None, excluded_machines=None, filesystem_diff=True
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_with_output(mock_lab, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_lab.name = "lab"
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = SaveCommand()
    command.run('.', ['-o', os.path.join('/out', 'my.tar')])
    mock_docker_manager.save_lab.assert_called_once_with(
        os.path.join('/out', 'my.tar'), lab=mock_lab,
        selected_machines=None, excluded_machines=None, filesystem_diff=True
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_name(mock_docker_manager, mock_manager_get_instance):
    mock_manager_get_instance.return_value = mock_docker_manager
    command = SaveCommand()
    command.run('.', ['-n', 'my_scenario'])
    mock_docker_manager.save_lab.assert_called_once_with(
        os.path.join(os.getcwd(), "my_scenario.tar"), lab_name='my_scenario',
        selected_machines=None, excluded_machines=None, filesystem_diff=True
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_full_images(mock_lab, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_lab.name = "lab"
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = SaveCommand()
    command.run('.', ['--full-images'])
    mock_docker_manager.save_lab.assert_called_once_with(
        os.path.join(os.getcwd(), "lab.tar"), lab=mock_lab,
        selected_machines=None, excluded_machines=None, filesystem_diff=False
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_with_selected_machines(mock_lab, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_lab.name = "lab"
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = SaveCommand()
    command.run('.', ['pc1', 'pc2'])
    mock_docker_manager.save_lab.assert_called_once_with(
        os.path.join(os.getcwd(), "lab.tar"), lab=mock_lab,
        selected_machines={'pc1', 'pc2'}, excluded_machines=None, filesystem_diff=True
    )


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_with_excluded_machines(mock_lab, mock_parse_lab, mock_docker_manager, mock_manager_get_instance):
    mock_lab.name = "lab"
    mock_parse_lab.return_value = mock_lab
    mock_manager_get_instance.return_value = mock_docker_manager
    command = SaveCommand()
    command.run('.', ['--exclude', 'pc1', 'pc2'])
    mock_docker_manager.save_lab.assert_called_once_with(
        os.path.join(os.getcwd(), "lab.tar"), lab=mock_lab,
        selected_machines=None, excluded_machines={'pc1', 'pc2'}, filesystem_diff=True
    )
