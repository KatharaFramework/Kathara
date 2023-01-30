import os
import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.ConnectCommand import ConnectCommand
from src.Kathara.model.Lab import Lab


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_tty")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_no_params(mock_lab, mock_parse_lab, mock_connect_tty):
    mock_parse_lab.return_value = mock_lab
    command = ConnectCommand()
    command.run('.', ['pc1'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_connect_tty.assert_called_once_with(machine_name="pc1", lab_hash=mock_lab.hash, shell=None, logs=False)


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_tty")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_with_directory(mock_lab, mock_parse_lab, mock_connect_tty):
    mock_parse_lab.return_value = mock_lab
    command = ConnectCommand()
    command.run('.', ['-d', '/test/path', 'pc1'])
    mock_parse_lab.assert_called_once_with('/test/path')
    mock_connect_tty.assert_called_once_with(machine_name="pc1", lab_hash=mock_lab.hash, shell=None, logs=False)


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_tty")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_with_logs(mock_lab, mock_parse_lab, mock_connect_tty):
    mock_parse_lab.return_value = mock_lab
    command = ConnectCommand()
    command.run('.', ['--logs', 'pc1'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_connect_tty.assert_called_once_with(machine_name="pc1", lab_hash=mock_lab.hash, shell=None, logs=True)


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_tty")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_with_shell(mock_lab, mock_parse_lab, mock_connect_tty):
    mock_parse_lab.return_value = mock_lab
    command = ConnectCommand()
    command.run('.', ['--shell', '/custom/shell', 'pc1'])
    mock_parse_lab.assert_called_once_with(os.getcwd())
    mock_connect_tty.assert_called_once_with(machine_name="pc1", lab_hash=mock_lab.hash, shell='/custom/shell',
                                             logs=False)


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_tty")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
def test_run_with_v_option(mock_parse_lab, mock_connect_tty):
    lab = Lab('kathara_vlab')
    command = ConnectCommand()
    command.run('.', ['-v', 'pc1'])
    assert not mock_parse_lab.called
    mock_connect_tty.assert_called_once_with(machine_name="pc1", lab_hash=lab.hash, shell=None,
                                             logs=False)


@mock.patch("src.Kathara.manager.Kathara.Kathara.connect_tty")
@mock.patch("src.Kathara.parser.netkit.LabParser.LabParser.parse")
@mock.patch("src.Kathara.model.Lab.Lab")
def test_run_all_params(mock_lab, mock_parse_lab, mock_connect_tty):
    mock_parse_lab.return_value = mock_lab
    command = ConnectCommand()
    command.run('.', ['-d', '/test/path', '--logs', '--shell', '/custom/shell', 'pc1'])
    mock_parse_lab.assert_called_once_with('/test/path')
    mock_connect_tty.assert_called_once_with(machine_name="pc1", lab_hash=mock_lab.hash, shell='/custom/shell',
                                             logs=True)
