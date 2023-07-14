import sys
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.cli.command.WipeCommand import WipeCommand
from src.Kathara.exceptions import PrivilegeError


@mock.patch("shutil.rmtree")
@mock.patch("src.Kathara.utils.get_vlab_temp_path")
@mock.patch("src.Kathara.cli.command.WipeCommand.confirmation_prompt")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_no_params(mock_docker_manager, mock_manager_get_instance,
                       mock_confirmation_prompt, mock_get_vlab_temp_path, mock_rm_tree):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_get_vlab_temp_path.return_value = '/vlab/path'
    command = WipeCommand()
    command.run('.', [])
    mock_confirmation_prompt.assert_called_once()
    mock_docker_manager.wipe.assert_called_once_with(all_users=False)
    mock_rm_tree.assert_called_once_with('/vlab/path', ignore_errors=True)


@mock.patch("shutil.rmtree")
@mock.patch("src.Kathara.utils.get_vlab_temp_path")
@mock.patch("src.Kathara.cli.command.WipeCommand.confirmation_prompt")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_force(mock_docker_manager, mock_manager_get_instance, mock_confirmation_prompt,
                        mock_get_vlab_temp_path, mock_rm_tree):
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_get_vlab_temp_path.return_value = '/vlab/path'
    command = WipeCommand()
    command.run('.', ['-f'])
    assert not mock_confirmation_prompt.called
    mock_docker_manager.wipe.assert_called_once_with(all_users=False)
    mock_rm_tree.assert_called_once_with('/vlab/path', ignore_errors=True)


@mock.patch("shutil.rmtree")
@mock.patch("src.Kathara.utils.get_vlab_temp_path")
@mock.patch("src.Kathara.setting.Setting.Setting.wipe_from_disk")
@mock.patch("src.Kathara.manager.Kathara.Kathara.wipe")
@mock.patch("src.Kathara.cli.command.WipeCommand.confirmation_prompt")
def test_run_with_setting(mock_confirmation_prompt, mock_wipe, mock_wipe_from_disk, mock_get_vlab_temp_path,
                          mock_rm_tree):
    mock_get_vlab_temp_path.return_value = '/vlab/path'
    command = WipeCommand()
    command.run('.', ['-s'])
    mock_confirmation_prompt.assert_called_once()
    mock_wipe_from_disk.assert_called_once()
    assert not mock_wipe.called
    assert not mock_rm_tree.called


@mock.patch("shutil.rmtree")
@mock.patch("src.Kathara.utils.get_vlab_temp_path")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.cli.command.WipeCommand.confirmation_prompt")
@mock.patch("src.Kathara.manager.Kathara.Kathara.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager")
def test_run_with_all(mock_docker_manager, mock_manager_get_instance, mock_confirmation_prompt, mock_is_admin,
                      mock_get_vlab_temp_path, mock_rm_tree):
    mock_get_vlab_temp_path.return_value = '/vlab/path'
    mock_manager_get_instance.return_value = mock_docker_manager
    mock_is_admin.return_value = True
    command = WipeCommand()
    command.run('.', ['-a'])
    mock_confirmation_prompt.assert_called_once()
    mock_docker_manager.wipe.assert_called_once_with(all_users=True)
    mock_rm_tree.assert_called_once_with('/vlab/path', ignore_errors=True)


@mock.patch("shutil.rmtree")
@mock.patch("src.Kathara.utils.get_vlab_temp_path")
@mock.patch("src.Kathara.manager.Kathara.Kathara.wipe")
@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.cli.command.WipeCommand.confirmation_prompt")
def test_run_with_all_no_root(mock_confirmation_prompt, mock_is_admin, mock_wipe, mock_get_vlab_temp_path,
                              mock_rm_tree):
    mock_get_vlab_temp_path.return_value = '/vlab/path'
    mock_is_admin.return_value = False
    command = WipeCommand()
    with pytest.raises(PrivilegeError):
        command.run('.', ['-a'])
    mock_confirmation_prompt.assert_called_once()
    assert not mock_wipe.called
    assert not mock_rm_tree.called
