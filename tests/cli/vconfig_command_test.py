import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.VconfigCommand import VconfigCommand


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_machine_to_link")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_machine_api_object")
def test_run_add_link(mock_get_machine_api_object, mock_connect_machine_to_link):
    command = VconfigCommand()
    command.run('.', ['-n', 'pc1', '--add', 'A'])
    mock_get_machine_api_object.assert_called_once_with('pc1', lab_name='kathara_vlab')
    mock_connect_machine_to_link.assert_called_once()


@mock.patch("src.Kathara.manager.Kathara.Kathara.disconnect_machine_from_link")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_link_api_object")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_machine_api_object")
def test_run_remove_link(mock_get_machine_api_object, mock_get_link_api_object, mock_disconnect_machine_from_link):
    command = VconfigCommand()
    command.run('.', ['-n', 'pc1', '--rm', 'A'])
    mock_get_machine_api_object.assert_called_once_with('pc1', lab_name='kathara_vlab')
    mock_get_link_api_object.assert_called_once_with('A', lab_name='kathara_vlab')
    mock_disconnect_machine_from_link.assert_called_once()
