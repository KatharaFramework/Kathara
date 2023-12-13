import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.VcleanCommand import VcleanCommand
from src.Kathara.model.Lab import Lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run(mock_docker_manager, mock_manager_get_instance):
    mock_manager_get_instance.return_value = mock_docker_manager
    lab = Lab('kathara_vlab')
    command = VcleanCommand()
    command.run('.', ['-n', 'pc1'])
    mock_docker_manager.undeploy_lab.assert_called_once_with(lab_name=lab.name, selected_machines={'pc1'})
