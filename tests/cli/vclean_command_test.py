import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.VcleanCommand import VcleanCommand
from src.Kathara.model.Lab import Lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.undeploy_lab")
def test_run(mock_undeploy_lab):
    lab = Lab('kathara_vlab')
    command = VcleanCommand()
    command.run('.', ['-n', 'pc1'])
    mock_undeploy_lab.assert_called_once_with(lab_name=lab.name, selected_machines={'pc1'})
