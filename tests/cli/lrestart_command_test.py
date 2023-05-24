import sys
from unittest import mock

sys.path.insert(0, './')

from src.Kathara.cli.command.LrestartCommand import LrestartCommand


@mock.patch("src.Kathara.cli.command.LstartCommand.LstartCommand.run")
@mock.patch("src.Kathara.cli.command.LcleanCommand.LcleanCommand.run")
def test_run_no_params(mock_lclean_run, mock_lstart_run):
    command = LrestartCommand()
    command.run('.', [])
    mock_lclean_run.assert_called_once_with('.', [])
    mock_lstart_run.assert_called_once_with('.', [])


@mock.patch("src.Kathara.cli.command.LstartCommand.LstartCommand.run")
@mock.patch("src.Kathara.cli.command.LcleanCommand.LcleanCommand.run")
def test_run_with_directory_absolute_path(mock_lclean_run, mock_lstart_run):
    command = LrestartCommand()
    arguments = ['-d', '/test/path']
    command.run('.', arguments)
    mock_lclean_run.assert_called_once_with('.', arguments)
    mock_lstart_run.assert_called_once_with('.', arguments)


@mock.patch("src.Kathara.cli.command.LstartCommand.LstartCommand.run")
@mock.patch("src.Kathara.cli.command.LcleanCommand.LcleanCommand.run")
def test_run_with_directory_relative_path(mock_lclean_run, mock_lstart_run):
    command = LrestartCommand()
    arguments = ['-d', 'test/path']
    command.run('.', arguments)
    mock_lclean_run.assert_called_once_with('.', arguments)
    mock_lstart_run.assert_called_once_with('.', arguments)


@mock.patch("src.Kathara.cli.command.LstartCommand.LstartCommand.run")
@mock.patch("src.Kathara.cli.command.LcleanCommand.LcleanCommand.run")
def test_run_with_params(mock_lclean_run, mock_lstart_run):
    command = LrestartCommand()
    path = '/test/path'
    arguments = ['-d', path, '--noterminals', 'pc1']
    command.run('.', arguments)
    mock_lclean_run.assert_called_once_with('.', ['-d', path, 'pc1'])
    mock_lstart_run.assert_called_once_with('.', arguments)
