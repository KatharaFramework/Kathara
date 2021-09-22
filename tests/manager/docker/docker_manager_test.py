import sys
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.docker.DockerManager import DockerManager
from src.Kathara.manager.docker.DockerImage import DockerImage
from src.Kathara.manager.docker.DockerMachine import DockerMachine
from src.Kathara.manager.docker.DockerLink import DockerLink
from src.Kathara.model.Lab import Lab


@pytest.fixture()
@mock.patch("docker.DockerClient")
def docker_manager(mock_docker_client):
    docker_manager = DockerManager()
    docker_manager.client = mock_docker_client
    docker_manager.docker_image = DockerImage(mock_docker_client)
    docker_manager.docker_machine = DockerMachine(mock_docker_client, docker_manager.docker_image)
    docker_manager.docker_link = DockerLink(mock_docker_client)
    return docker_manager


@pytest.fixture()
def two_device_scenario():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc1.name, "B")
    lab.connect_machine_to_link(pc2.name, "A")
    return lab


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.deploy_machines")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.deploy_links")
def test_deploy_lab(mock_deploy_links, mock_deploy_machines, docker_manager, two_device_scenario):
    docker_manager.deploy_lab(two_device_scenario)
    mock_deploy_links.assert_called_once_with(two_device_scenario)
    mock_deploy_machines.assert_called_once_with(two_device_scenario)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.deploy_lab")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.update")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.create")
def test_update_lab_empty_lab(mock_create_link, mock_update_machine, mock_deploy_lab, docker_manager,
                              two_device_scenario):
    docker_manager.update_lab(two_device_scenario)
    links = list(two_device_scenario.links.values())
    mock_create_link.assert_any_call(links.pop())
    mock_create_link.assert_any_call(links.pop())
    assert mock_create_link.call_count == 2
    assert len(links) == 0
    machines = list(two_device_scenario.machines.values())
    mock_deploy_lab.assert_any_call(two_device_scenario, selected_machines={machines.pop().name})
    mock_deploy_lab.assert_any_call(two_device_scenario, selected_machines={machines.pop().name})
    assert mock_deploy_lab.call_count == 2
    assert len(machines) == 0


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.deploy_lab")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.update")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.create")
def test_update_lab_update_machine(mock_create_link, mock_update_machine, mock_deploy_lab, docker_manager,
                                   two_device_scenario):
    two_device_scenario.machines['pc1'].api_object = Mock()
    docker_manager.update_lab(two_device_scenario)
    links = list(two_device_scenario.links.values())
    mock_create_link.assert_any_call(links.pop())
    mock_create_link.assert_any_call(links.pop())
    assert mock_create_link.call_count == 2
    assert len(links) == 0
    mock_deploy_lab.assert_called_once_with(two_device_scenario, selected_machines={"pc2"})
    assert mock_deploy_lab.call_count == 1
    mock_update_machine.assert_called_once_with(two_device_scenario.machines['pc1'])


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_lab(mock_undeploy_machine, mock_undeploy_link, docker_manager):
    docker_manager.undeploy_lab('lab_hash')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines=None)
    mock_undeploy_link.assert_called_once_with('lab_hash')


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_lab_selected_machines(mock_undeploy_machine, mock_undeploy_link, docker_manager):
    docker_manager.undeploy_lab('lab_hash', selected_machines={'pc1', 'pc2'})
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines={'pc1', 'pc2'})
    mock_undeploy_link.assert_called_once_with('lab_hash')


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.wipe")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.wipe")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_wipe(mock_get_current_user_name, mock_wipe_machines, mock_wipe_links, docker_manager):
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.wipe()
    mock_get_current_user_name.assert_called_once()
    mock_wipe_machines.assert_called_once_with(user="kathara_user")
    mock_wipe_links.assert_called_once_with(user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.wipe")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.wipe")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_wipe_all_users(mock_get_current_user_name, mock_wipe_machines, mock_wipe_links, docker_manager):
    docker_manager.wipe(all_users=True)
    assert not mock_get_current_user_name.called
    mock_wipe_machines.assert_called_once_with(user=None)
    mock_wipe_links.assert_called_once_with(user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.wipe")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.wipe")
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_wipe_all_users_and_multiuser(mock_setting_get_instance, mock_get_current_user_name, mock_wipe_machines,
                                      mock_wipe_links, docker_manager):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': True
    })
    mock_setting_get_instance.return_value = setting_mock
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.wipe(all_users=True)
    assert mock_get_current_user_name.called
    mock_wipe_machines.assert_called_once()
    mock_wipe_links.assert_called_once()
