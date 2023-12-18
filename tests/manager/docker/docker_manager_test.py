import sys
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.docker.DockerManager import DockerManager
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Link import Link
from src.Kathara.utils import generate_urlsafe_hash
from src.Kathara.manager.docker.stats.DockerLinkStats import DockerLinkStats
from src.Kathara.manager.docker.stats.DockerMachineStats import DockerMachineStats
from src.Kathara.exceptions import MachineNotFoundError, LabNotFoundError, InvocationError, LinkNotFoundError, \
    MachineNotRunningError


#
#  FIXTURE
#
@pytest.fixture()
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin.check_and_download_plugin")
@mock.patch("docker.from_env")
def docker_manager(mock_from_env, mock_check_and_download_plugin):
    mock_check_and_download_plugin.return_value = True
    mock_from_env.return_value = Mock()
    docker_manager = DockerManager()

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


@pytest.fixture()
@mock.patch("docker.models.containers.Container")
def default_device(mock_docker_container):
    device = Machine(Lab('Default scenario'), "test_device")
    device.add_meta("exec", "ls")
    device.add_meta("mem", "64m")
    device.add_meta("cpus", "2")
    device.add_meta("image", "kathara/test")
    device.add_meta("bridged", False)
    device.api_object = mock_docker_container
    mock_docker_container.status = "running"
    return device


@pytest.fixture()
def default_link():
    from src.Kathara.model.Link import Link
    return Link(Lab("default_scenario"), "A")


@pytest.fixture()
def default_link_b():
    from src.Kathara.model.Link import Link
    return Link(Lab("default_scenario"), "B")


@pytest.fixture()
def default_link_c():
    from src.Kathara.model.Link import Link
    return Link(Lab("default_scenario"), "C")


@pytest.fixture()
@mock.patch("docker.models.networks.Network")
def docker_network(mock_network):
    mock_network.name = "kathara_user_hash_test_network"
    mock_network.attrs = {
        "Labels": {
            "name": "test_network",
            "lab_hash": "lab_hash",
            "user": "user",
            "external": []
        }
    }
    return mock_network


@pytest.fixture()
@mock.patch("docker.models.networks.Network")
def docker_network_b(mock_network):
    mock_network.name = "kathara_user_hash_test_network_b"
    mock_network.attrs = {
        "Labels": {
            "name": "test_network_b",
            "lab_hash": "lab_hash",
            "user": "user",
            "external": []
        }
    }
    return mock_network


@pytest.fixture()
@mock.patch("docker.models.containers.Container")
def docker_container(mock_container):
    mock_container.reload = Mock()
    mock_container.labels = {
        "name": "test_container"
    }
    mock_container.attrs = {"HostConfig": {
        "Privileged": True,
        "Memory": 67108864,
        "NanoCpus": 100000000,
        "PortBindings": {
            "55/udp": [
                {
                    "HostIp": "",
                    "HostPort": "3000"
                }
            ]
        },
        "Sysctls": {
            "sysctl.test": "0",
        },
    }, "Config": {
        "Image": "test_image",
        "Labels": {
            "shell": "/bin/bash"
        },
        "Env": [
            "test=path"
        ]
    }, "NetworkSettings": {
        "Networks": {
            "kathara_user_hash_test_network": {
                "Links": None,
            },
            "bridge": {}
        }
    }}

    return mock_container


@pytest.fixture()
@mock.patch("docker.models.containers.Container")
def docker_container_empty_meta(mock_container):
    mock_container.reload = Mock()
    mock_container.labels = {
        "name": "test_container"
    }
    mock_container.attrs = {
        "HostConfig": {
            "Privileged": False,
            "Memory": 0,
            "NanoCpus": 0,
            "PortBindings": None,
            "Sysctls": {
                "sysctl.test": "0",
            },
        },
        "Config": {
            "Image": "test_image",
            "Labels": {
                "shell": "/bin/bash"
            },
            "Env": [
                "test=path"
            ]
        },
        "NetworkSettings": {
            "Networks": {
                "none": {}
            }
        }
    }

    return mock_container


#
# TEST: deploy_lab
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.deploy_machines")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.deploy_links")
def test_deploy_lab(mock_deploy_links, mock_deploy_machines, docker_manager, two_device_scenario):
    docker_manager.deploy_lab(two_device_scenario)
    mock_deploy_links.assert_called_once_with(two_device_scenario, selected_links=None)
    mock_deploy_machines.assert_called_once_with(two_device_scenario, selected_machines=None)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.deploy_machines")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.deploy_links")
def test_deploy_lab_selected_machines(mock_deploy_links, mock_deploy_machines, docker_manager,
                                      two_device_scenario: Lab):
    docker_manager.deploy_lab(two_device_scenario, selected_machines={"pc1"})

    mock_deploy_links.assert_called_once_with(two_device_scenario, selected_links={"A", "B"})
    mock_deploy_machines.assert_called_once_with(two_device_scenario, selected_machines={"pc1"})


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.deploy_machines")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.deploy_links")
def test_deploy_lab_selected_machines_exception(mock_deploy_links, mock_deploy_machines, docker_manager,
                                                two_device_scenario: Lab):
    with pytest.raises(MachineNotFoundError):
        docker_manager.deploy_lab(two_device_scenario, selected_machines={"pc3"})
    assert not mock_deploy_machines.called
    assert not mock_deploy_links.called


#
# TEST: deploy_machine
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.deploy_links")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.deploy_machines")
def test_deploy_machine(mock_deploy_machines, mock_deploy_links, docker_manager, default_device, default_link):
    default_device.add_interface(default_link)

    docker_manager.deploy_machine(default_device)
    mock_deploy_links.assert_called_once_with(default_device.lab, selected_links={default_link.name})
    mock_deploy_machines.assert_called_once_with(default_device.lab, selected_machines={default_device.name})


def test_deploy_machine_no_lab(docker_manager, default_device):
    default_device.lab = None

    with pytest.raises(LabNotFoundError):
        docker_manager.deploy_machine(default_device)


#
# TEST: deploy_link
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.deploy_links")
def test_deploy_link(mock_deploy_links, docker_manager, default_link):
    docker_manager.deploy_link(default_link)
    mock_deploy_links.assert_called_once_with(default_link.lab, selected_links={default_link.name})


def test_deploy_link_no_lab(docker_manager, default_link):
    default_link.lab = None

    with pytest.raises(LabNotFoundError):
        docker_manager.deploy_link(default_link)


#
# TEST: connect_machine_to_link
#
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.deploy_link")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect_to_link")
def test_connect_machine_to_link_one_link(mock_connect_to_link_machine, mock_deploy_link, docker_manager,
                                          default_device, default_link):
    docker_manager.connect_machine_to_link(default_device, default_link)

    mock_deploy_link.assert_called_once_with(default_link)
    mock_connect_to_link_machine.assert_called_once_with(default_device, default_link)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.deploy_link")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect_to_link")
def test_connect_machine_to_link_two_links(mock_connect_to_link_machine, mock_deploy_link, docker_manager,
                                           default_device, default_link, default_link_b):
    docker_manager.connect_machine_to_link(default_device, default_link)

    mock_deploy_link.assert_called_with(default_link)
    mock_connect_to_link_machine.assert_called_with(default_device, default_link)

    docker_manager.connect_machine_to_link(default_device, default_link_b)

    mock_deploy_link.assert_called_with(default_link_b)
    mock_connect_to_link_machine.assert_called_with(default_device, default_link_b)

    assert mock_deploy_link.call_count == 2
    assert mock_connect_to_link_machine.call_count == 2


def test_connect_machine_to_link_no_machine_lab(docker_manager, default_device, default_link):
    default_device.lab = None

    with pytest.raises(LabNotFoundError):
        docker_manager.connect_machine_to_link(default_device, default_link)


def test_connect_machine_to_link_no_link_lab(docker_manager, default_device, default_link):
    default_link.lab = None

    with pytest.raises(LabNotFoundError):
        docker_manager.connect_machine_to_link(default_device, default_link)


def test_connect_machine_to_link_machine_not_running_error(docker_manager, default_device, default_link):
    default_device.api_object = None

    with pytest.raises(MachineNotRunningError):
        docker_manager.connect_machine_to_link(default_device, default_link)


def test_connect_machine_to_link_machine_exited_error(docker_manager, default_device, default_link):
    default_device.api_object.status = "exited"

    with pytest.raises(MachineNotRunningError):
        docker_manager.connect_machine_to_link(default_device, default_link)


#
# TEST: disconnect_machine_from_link
#
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.disconnect_from_link")
def test_disconnect_machine_from_link_one_link(mock_disconnect_from_link_machine, mock_undeploy_link, docker_manager,
                                               default_device, default_link):
    default_device.add_interface(default_link)

    docker_manager.disconnect_machine_from_link(default_device, default_link)

    mock_undeploy_link.assert_called_once_with(default_link)
    mock_disconnect_from_link_machine.assert_called_once_with(default_device, default_link)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.undeploy_link")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.disconnect_from_link")
def test_disconnect_machine_from_link_two_links(mock_disconnect_from_link_machine, mock_undeploy_link, docker_manager,
                                                default_device, default_link, default_link_b):
    default_device.add_interface(default_link)
    default_device.add_interface(default_link_b)

    docker_manager.disconnect_machine_from_link(default_device, default_link)

    mock_undeploy_link.assert_called_with(default_link)
    mock_disconnect_from_link_machine.assert_called_with(default_device, default_link)

    docker_manager.disconnect_machine_from_link(default_device, default_link_b)

    mock_undeploy_link.assert_called_with(default_link_b)
    mock_disconnect_from_link_machine.assert_called_with(default_device, default_link_b)

    assert mock_undeploy_link.call_count == 2
    assert mock_disconnect_from_link_machine.call_count == 2


def test_disconnect_machine_from_link_no_machine_lab(docker_manager, default_device, default_link):
    default_device.lab = None

    default_device.add_interface(default_link)

    with pytest.raises(LabNotFoundError):
        docker_manager.disconnect_machine_from_link(default_device, default_link)


def test_disconnect_machine_from_link_no_link_lab(docker_manager, default_device, default_link):
    default_link.lab = None

    default_device.add_interface(default_link)

    with pytest.raises(LabNotFoundError):
        docker_manager.disconnect_machine_from_link(default_device, default_link)


#
# TEST: undeploy_machine
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_machine(mock_machine_undeploy, mock_link_undeploy, docker_manager, default_device, default_link):
    default_device.add_interface(default_link)

    docker_manager.undeploy_machine(default_device)

    mock_machine_undeploy.assert_called_once_with(default_device.lab.hash, selected_machines={default_device.name})
    mock_link_undeploy.assert_called_once_with(default_device.lab.hash, selected_links={default_link.name})


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_machine_two_machines(mock_machine_undeploy, mock_link_undeploy, docker_manager, two_device_scenario):
    device_1 = two_device_scenario.get_or_new_machine('pc1')
    device_1_links = {x.name for x in device_1.interfaces.values()}

    docker_manager.undeploy_machine(device_1)

    mock_machine_undeploy.assert_called_once_with(two_device_scenario.hash, selected_machines={device_1.name})
    mock_link_undeploy.assert_called_once_with(two_device_scenario.hash, selected_links=device_1_links)


def test_undeploy_machine_no_lab(docker_manager, default_device):
    default_device.lab = None

    with pytest.raises(LabNotFoundError):
        docker_manager.undeploy_machine(default_device)


#
# TEST: undeploy_link
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
def test_undeploy_link(mock_link_undeploy, docker_manager, default_link):
    docker_manager.undeploy_link(default_link)
    mock_link_undeploy.assert_called_once_with(default_link.lab.hash, selected_links={default_link.name})


def test_undeploy_link_no_lab(docker_manager, default_link):
    default_link.lab = None

    with pytest.raises(LabNotFoundError):
        docker_manager.undeploy_link(default_link)


#
# TEST: undeploy_lab
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_lab(mock_undeploy_machine, mock_undeploy_link, docker_manager):
    docker_manager.undeploy_lab(lab_hash='lab_hash')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines=None)
    mock_undeploy_link.assert_called_once_with('lab_hash')


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_lab_selected_machines(mock_undeploy_machine, mock_undeploy_link, docker_manager):
    docker_manager.undeploy_lab(lab_hash='lab_hash', selected_machines={'pc1', 'pc2'})
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines={'pc1', 'pc2'})
    mock_undeploy_link.assert_called_once_with('lab_hash')


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
@mock.patch("src.Kathara.utils.generate_urlsafe_hash")
def test_undeploy_lab_lab_name(mock_generate_urlsafe_hash, mock_undeploy_machine, mock_undeploy_link, docker_manager):
    mock_generate_urlsafe_hash.return_value = "lab_hash"

    docker_manager.undeploy_lab(lab_name='lab_name')
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines=None)
    mock_undeploy_link.assert_called_once_with('lab_hash')
    mock_generate_urlsafe_hash.assert_called_once_with("lab_name")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
@mock.patch("src.Kathara.utils.generate_urlsafe_hash")
def test_undeploy_lab_lab_name_selected_machines(mock_generate_urlsafe_hash,
                                                 mock_undeploy_machine, mock_undeploy_link, docker_manager):
    mock_generate_urlsafe_hash.return_value = "lab_hash"

    docker_manager.undeploy_lab(lab_name='lab_name', selected_machines={'pc1', 'pc2'})
    mock_undeploy_machine.assert_called_once_with('lab_hash', selected_machines={'pc1', 'pc2'})
    mock_undeploy_link.assert_called_once_with('lab_hash')
    mock_generate_urlsafe_hash.assert_called_once_with("lab_name")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_lab_lab_obj(mock_undeploy_machine, mock_undeploy_link, docker_manager, two_device_scenario):
    expected_hash = two_device_scenario.hash

    docker_manager.undeploy_lab(lab=two_device_scenario)
    mock_undeploy_machine.assert_called_once_with(expected_hash, selected_machines=None)
    mock_undeploy_link.assert_called_once_with(expected_hash)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.undeploy")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.undeploy")
def test_undeploy_lab_lab_obj_selected_machines(mock_undeploy_machine, mock_undeploy_link, docker_manager,
                                                two_device_scenario):
    expected_hash = two_device_scenario.hash

    docker_manager.undeploy_lab(lab=two_device_scenario, selected_machines={'pc1', 'pc2'})
    mock_undeploy_machine.assert_called_once_with(expected_hash, selected_machines={'pc1', 'pc2'})
    mock_undeploy_link.assert_called_once_with(expected_hash)


#
# TEST: wipe
#
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
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_wipe_all_users(mock_setting_get_instance, mock_get_current_user_name, mock_wipe_machines, mock_wipe_links,
                        docker_manager):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cd': False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock

    docker_manager.wipe(all_users=True)
    assert not mock_get_current_user_name.called
    mock_wipe_machines.assert_called_once_with(user=None)
    mock_wipe_links.assert_called_once_with(user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.wipe")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.wipe")
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_wipe_all_users_and_shared_cd(mock_setting_get_instance, mock_get_current_user_name, mock_wipe_machines,
                                      mock_wipe_links, docker_manager):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cd': True,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.wipe(all_users=True)
    assert not mock_get_current_user_name.called
    mock_wipe_machines.assert_called_once_with(user=None)
    mock_wipe_links.assert_called_once_with(user=None)


#
# TEST: connect_tty
#
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect")
def test_connect_tty_lab_hash(mock_connect, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.connect_tty(default_device.name,
                               lab_hash=default_device.lab.hash)

    mock_connect.assert_called_once_with(lab_hash=default_device.lab.hash,
                                         machine_name=default_device.name,
                                         user="kathara_user",
                                         shell=None,
                                         logs=False,
                                         wait=True)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect")
def test_connect_tty_lab_name(mock_connect, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.connect_tty(default_device.name,
                               lab_name=default_device.lab.name)

    mock_connect.assert_called_once_with(lab_hash=generate_urlsafe_hash(default_device.lab.name),
                                         machine_name=default_device.name,
                                         user="kathara_user",
                                         shell=None,
                                         logs=False,
                                         wait=True)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect")
def test_connect_tty_with_custom_shell(mock_connect, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.connect_tty(default_device.name,
                               lab_hash=default_device.lab.hash,
                               shell="/usr/bin/zsh")

    mock_connect.assert_called_once_with(lab_hash=default_device.lab.hash,
                                         machine_name=default_device.name,
                                         user="kathara_user",
                                         shell="/usr/bin/zsh",
                                         logs=False,
                                         wait=True)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect")
def test_connect_tty_with_logs(mock_connect, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.connect_tty(default_device.name,
                               lab_hash=default_device.lab.hash,
                               logs=True)

    mock_connect.assert_called_once_with(lab_hash=default_device.lab.hash,
                                         machine_name=default_device.name,
                                         user="kathara_user",
                                         shell=None,
                                         logs=True,
                                         wait=True)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.connect")
def test_connect_tty_error(mock_connect, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    with pytest.raises(InvocationError):
        docker_manager.connect_tty(default_device.name)

    assert not mock_connect.called


#
# TEST: exec
#
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.exec")
def test_exec_lab_hash(mock_exec, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.exec(default_device.name, ["test", "command"], lab_hash=default_device.lab.hash)

    mock_exec.assert_called_once_with(
        default_device.lab.hash,
        default_device.name,
        ["test", "command"],
        user="kathara_user",
        tty=False,
        wait=False
    )


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.exec")
def test_exec_lab_name(mock_exec, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.exec(default_device.name, ["test", "command"], lab_name=default_device.lab.name)

    mock_exec.assert_called_once_with(
        generate_urlsafe_hash(default_device.lab.name),
        default_device.name,
        ["test", "command"],
        user="kathara_user",
        tty=False,
        wait=False
    )


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.exec")
def test_exec_wait(mock_exec, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    docker_manager.exec(default_device.name, ["test", "command"], lab_hash=default_device.lab.hash, wait=True)

    mock_exec.assert_called_once_with(
        default_device.lab.hash,
        default_device.name,
        ["test", "command"],
        user="kathara_user",
        tty=False,
        wait=True
    )


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.exec")
def test_exec_invocation_error(mock_exec, mock_get_current_user_name, docker_manager, default_device):
    mock_get_current_user_name.return_value = "kathara_user"

    with pytest.raises(InvocationError):
        docker_manager.exec(default_device.name, ["test", "command"])

    assert not mock_exec.called


#
# TEST: get_machine_api_object
#
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_hash_user(mock_get_machines_api_objects, mock_get_current_user_name,
                                              docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_machine_api_object("test_device", "lab_hash_value", all_users=False)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash="lab_hash_value",
                                                          machine_name="test_device", user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_hash_no_user(mock_get_machines_api_objects, docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    docker_manager.get_machine_api_object("test_device", "lab_hash_value", all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash="lab_hash_value",
                                                          machine_name="test_device", user=None)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_name_user(mock_get_machines_api_objects, mock_get_current_user_name,
                                              docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_machine_api_object("test_device", lab_name="lab_name", all_users=False)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"),
                                                          machine_name="test_device", user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_lab_name_no_user(mock_get_machines_api_objects, docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    docker_manager.get_machine_api_object("test_device", lab_name="lab_name", all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"),
                                                          machine_name="test_device", user=None)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_no_name_no_hash(mock_get_machines_api_objects, docker_manager, default_device):
    with pytest.raises(InvocationError):
        docker_manager.get_machine_api_object("test_device", all_users=True)
    assert not mock_get_machines_api_objects.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machine_api_object_device_not_found(mock_get_machines_api_objects, docker_manager, default_device):
    mock_get_machines_api_objects.return_value = []
    with pytest.raises(MachineNotFoundError):
        docker_manager.get_machine_api_object("test_device", lab_name="lab_name", all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"),
                                                          machine_name="test_device", user=None)


#
# TEST: get_machines_api_objects
#
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_hash_user(mock_get_machines_api_objects, mock_get_current_user_name,
                                                docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_machines_api_objects(lab_hash="lab_hash_value", all_users=False)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash="lab_hash_value", user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_hash_no_user(mock_get_machines_api_objects, docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    docker_manager.get_machines_api_objects(lab_hash="lab_hash_value", all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash="lab_hash_value", user=None)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_name_user(mock_get_machines_api_objects, mock_get_current_user_name,
                                                docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_machines_api_objects(lab_name="lab_name", all_users=False)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"),
                                                          user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_lab_name_no_user(mock_get_machines_api_objects, docker_manager, default_device):
    mock_get_machines_api_objects.return_value = [default_device.api_object]
    docker_manager.get_machines_api_objects(lab_name="lab_name", all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"), user=None)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_no_name_no_hash(mock_get_machines_api_objects, docker_manager):
    docker_manager.get_machines_api_objects(all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=None, user=None)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_api_objects_device_not_found(mock_get_machines_api_objects, docker_manager):
    mock_get_machines_api_objects.return_value = []
    machines = docker_manager.get_machines_api_objects(lab_name="lab_name", all_users=True)
    mock_get_machines_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"), user=None)
    assert not machines


#
# TESTS: get_link_api_object
#
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_hash_user(mock_get_links_api_objects, mock_get_current_user_name, docker_manager,
                                           docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_link_api_object("test_link", lab_hash="lab_hash_value", all_users=False)
    mock_get_links_api_objects.assert_called_once_with(lab_hash="lab_hash_value",
                                                       link_name="test_link", user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_hash_no_user(mock_get_links_api_objects, docker_manager,
                                              docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    docker_manager.get_link_api_object("test_link", lab_hash="lab_hash_value", all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash="lab_hash_value",
                                                       link_name="test_link", user=None)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_name_user(mock_get_links_api_objects, mock_get_current_user_name,
                                           docker_manager, docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_link_api_object("test_link", lab_name="lab_name_value", all_users=False)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name_value"),
                                                       link_name="test_link", user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_link_api_object_lab_name_no_user(mock_get_links_api_objects,
                                              docker_manager, docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    docker_manager.get_link_api_object("test_link", lab_name="lab_name_value", all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name_value"),
                                                       link_name="test_link", user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_link_api_object_no_name_no_hash(mock_get_links_api_objects, docker_manager):
    with pytest.raises(InvocationError):
        docker_manager.get_link_api_object("test_link", all_users=True)
    assert not mock_get_links_api_objects.called


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_link_api_object_not_found(mock_get_links_api_objects,
                                       docker_manager):
    mock_get_links_api_objects.return_value = []
    with pytest.raises(LinkNotFoundError):
        docker_manager.get_link_api_object("test_link", lab_name="lab_name_value", all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name_value"),
                                                       link_name="test_link", user=None)


#
# TESTS: get_links_api_objects
#
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_hash_user(mock_get_links_api_objects, mock_get_current_user_name, docker_manager,
                                             docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_links_api_objects(lab_hash="lab_hash_value", all_users=False)
    mock_get_links_api_objects.assert_called_once_with(lab_hash="lab_hash_value", user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_hash_no_user(mock_get_links_api_objects, docker_manager,
                                                docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    docker_manager.get_links_api_objects(lab_hash="lab_hash_value", all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash="lab_hash_value", user=None)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_name_user(mock_get_links_api_objects, mock_get_current_user_name,
                                             docker_manager, docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    mock_get_current_user_name.return_value = "kathara_user"
    docker_manager.get_links_api_objects(lab_name="lab_name_value", all_users=False)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name_value"),
                                                       user="kathara_user")


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_lab_name_no_user(mock_get_links_api_objects,
                                                docker_manager, docker_network):
    mock_get_links_api_objects.return_value = [docker_network]
    docker_manager.get_links_api_objects(lab_name="lab_name_value", all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name_value"),
                                                       user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_no_name_no_hash(mock_get_links_api_objects, docker_manager):
    docker_manager.get_links_api_objects(all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=None, user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_api_objects_by_filters")
def test_get_links_api_objects_not_found(mock_get_links_api_objects, docker_manager):
    mock_get_links_api_objects.return_value = []
    links = docker_manager.get_links_api_objects(lab_name="lab_name_value", all_users=True)
    mock_get_links_api_objects.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name_value"), user=None)
    assert not links


#
# TESTS: get_lab_from_api
#
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_api_objects")
def test_get_lab_from_api_lab_name_all_info(mock_get_links_api_objects, mock_get_machines_api_objects, docker_container,
                                            docker_network, docker_manager):
    mock_get_machines_api_objects.return_value = [docker_container]
    mock_get_links_api_objects.return_value = [docker_network]
    lab = docker_manager.get_lab_from_api(lab_name="lab_test")
    assert len(lab.machines) == 1
    assert docker_container.labels["name"] in lab.machines
    reconstructed_device = lab.get_or_new_machine(docker_container.labels["name"])
    assert reconstructed_device.meta["privileged"]
    assert reconstructed_device.meta["image"] == "test_image"
    assert reconstructed_device.meta["shell"] == "/bin/bash"
    assert reconstructed_device.meta["mem"] == "64M"
    assert reconstructed_device.meta["cpu"] == 0.1
    assert reconstructed_device.meta["envs"]["test"] == "path"
    assert reconstructed_device.meta["ports"][(3000, "udp")] == 55
    assert reconstructed_device.meta["sysctls"]["sysctl.test"] == "0"
    assert len(lab.links) == 1
    assert docker_network.attrs["Labels"]["name"] in lab.links


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_api_objects")
def test_get_lab_from_api_lab_hash_all_info(mock_get_links_api_objects, mock_get_machines_api_objects, docker_container,
                                            docker_network, docker_manager):
    mock_get_machines_api_objects.return_value = [docker_container]
    mock_get_links_api_objects.return_value = [docker_network]
    lab = docker_manager.get_lab_from_api(lab_hash="lab_hash")
    assert lab.hash == "lab_hash"
    assert lab.name == "reconstructed_lab"
    assert len(lab.machines) == 1
    assert docker_container.labels["name"] in lab.machines
    reconstructed_device = lab.get_or_new_machine(docker_container.labels["name"])
    assert reconstructed_device.meta["privileged"]
    assert reconstructed_device.meta["image"] == "test_image"
    assert reconstructed_device.meta["shell"] == "/bin/bash"
    assert reconstructed_device.meta["mem"] == "64M"
    assert reconstructed_device.meta["cpu"] == 0.1
    assert reconstructed_device.meta["envs"]["test"] == "path"
    assert reconstructed_device.meta["ports"][(3000, "udp")] == 55
    assert reconstructed_device.meta["sysctls"]["sysctl.test"] == "0"
    assert reconstructed_device.meta["bridged"]
    assert len(lab.links) == 1
    assert docker_network.attrs["Labels"]["name"] in lab.links


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_api_objects")
def test_get_lab_from_api_lab_name_empty_meta(mock_get_links_api_objects, mock_get_machines_api_objects,
                                              docker_container_empty_meta, docker_manager):
    mock_get_machines_api_objects.return_value = [docker_container_empty_meta]
    mock_get_links_api_objects.return_value = []
    lab = docker_manager.get_lab_from_api(lab_name="lab_test")
    assert len(lab.machines) == 1
    assert docker_container_empty_meta.labels["name"] in lab.machines
    reconstructed_device = lab.get_or_new_machine(docker_container_empty_meta.labels["name"])
    assert not reconstructed_device.meta["privileged"]
    assert reconstructed_device.meta["image"] == "test_image"
    assert reconstructed_device.meta["shell"] == "/bin/bash"
    assert "mem" not in reconstructed_device.meta
    assert "cpu" not in reconstructed_device.meta
    assert reconstructed_device.meta["envs"]["test"] == "path"
    assert reconstructed_device.meta["ports"] == {}
    assert reconstructed_device.meta["sysctls"]["sysctl.test"] == "0"
    assert len(lab.links) == 0


def test_get_lab_from_api_exception(docker_manager):
    with pytest.raises(InvocationError):
        docker_manager.get_lab_from_api()


#
# TESTS: update_lab_from_api
#
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_api_objects")
def test_update_lab_from_api_add_link(mock_get_links_api_objects, mock_get_machines_api_objects, docker_container,
                                      docker_network, docker_network_b, docker_manager):
    lab = Lab("test")
    device = lab.get_or_new_machine(docker_container.labels["name"])
    link = Link(lab, docker_network.attrs["Labels"]["name"])
    device.add_interface(link)
    mock_get_machines_api_objects.return_value = [docker_container]
    mock_get_links_api_objects.return_value = [docker_network, docker_network_b]
    docker_container.attrs["NetworkSettings"]["Networks"] = ["kathara_user_hash_test_network",
                                                             "kathara_user_hash_test_network_b"]
    docker_manager.update_lab_from_api(lab)
    assert len(lab.machines) == 1
    assert docker_container.labels["name"] in lab.machines
    assert len(lab.links) == 2
    assert docker_network.attrs["Labels"]["name"] in lab.links
    assert docker_network_b.attrs["Labels"]["name"] in lab.links


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_api_objects")
def test_update_lab_from_api_remove_link(mock_get_links_api_objects, mock_get_machines_api_objects, docker_container,
                                         docker_network, docker_manager):
    lab = Lab("test")
    device = lab.get_or_new_machine(docker_container.labels["name"])
    link = Link(lab, docker_network.attrs["Labels"]["name"])
    device.add_interface(link)
    mock_get_machines_api_objects.return_value = [docker_container]
    mock_get_links_api_objects.return_value = []
    docker_container.attrs["NetworkSettings"]["Networks"] = []

    docker_manager.update_lab_from_api(lab)
    assert len(lab.machines) == 1
    assert docker_container.labels["name"] in lab.machines
    assert len(lab.links) == 0


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_api_objects")
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_api_objects")
def test_update_lab_from_api_add_remove_link(mock_get_links_api_objects, mock_get_machines_api_objects,
                                             docker_container,
                                             docker_network, docker_network_b, docker_manager):
    lab = Lab("test")
    device = lab.get_or_new_machine(docker_container.labels["name"])
    link = Link(lab, docker_network.attrs["Labels"]["name"])
    device.add_interface(link)

    mock_get_machines_api_objects.return_value = [docker_container]
    mock_get_links_api_objects.return_value = [docker_network_b]
    docker_container.attrs["NetworkSettings"]["Networks"] = ["kathara_user_hash_test_network_b"]

    docker_manager.update_lab_from_api(lab)
    assert len(lab.machines) == 1
    assert docker_container.labels["name"] in lab.machines
    assert len(lab.links) == 1
    assert docker_network_b.attrs["Labels"]["name"] in lab.links


#
# TESTS: get_machines_stats
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_stats")
def test_get_machines_stats_lab_hash_no_user(mock_get_machines_stats, docker_manager):
    docker_manager.get_machines_stats(lab_hash="lab_hash", all_users=True)
    mock_get_machines_stats.assert_called_once_with(lab_hash="lab_hash", machine_name=None,
                                                    user=None)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_stats")
def test_get_machines_stats_lab_name_no_user(mock_get_machines_stats, docker_manager):
    docker_manager.get_machines_stats(lab_name="lab_name", all_users=True)
    mock_get_machines_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"), machine_name=None,
                                                    user=None)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_stats")
def test_get_machines_stats_lab_hash_user(mock_get_machines_stats, mock_get_current_user_name, docker_manager):
    mock_get_current_user_name.return_value = "kathara-user"
    docker_manager.get_machines_stats(lab_hash="lab_hash")
    mock_get_machines_stats.assert_called_once_with(lab_hash="lab_hash", machine_name=None, user="kathara-user")


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_stats")
def test_get_machines_stats_no_name_no_hash(mock_get_machines_stats, docker_manager):
    docker_manager.get_machines_stats(all_users=True)
    mock_get_machines_stats.assert_called_once_with(lab_hash=None, machine_name=None, user=None)


#
# TESTS: get_machine_stats
#
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_stats")
def test_get_machine_stats_lab_hash_no_user(mock_get_machines_stats, default_device, docker_manager):
    mock_get_machines_stats.return_value = iter([{"test_device": DockerMachineStats(default_device.api_object)}])
    next(docker_manager.get_machine_stats(machine_name="test_device", lab_hash="lab_hash", all_users=True))
    mock_get_machines_stats.assert_called_once_with(lab_hash="lab_hash", machine_name="test_device",
                                                    all_users=True)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_stats")
def test_get_machine_stats_lab_name_no_user(mock_get_machines_stats, default_device, docker_manager):
    mock_get_machines_stats.return_value = iter([{"test_device": DockerMachineStats(default_device.api_object)}])
    next(docker_manager.get_machine_stats(machine_name="test_device", lab_name="lab_name", all_users=True))
    mock_get_machines_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"),
                                                    machine_name="test_device",
                                                    all_users=True)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_stats")
def test_get_machine_stats_lab_hash_user(mock_get_machines_stats, default_device, docker_manager):
    mock_get_machines_stats.return_value = iter([{"test_device": DockerMachineStats(default_device.api_object)}])
    next(docker_manager.get_machine_stats(machine_name="test_device", lab_hash="lab_hash"))
    mock_get_machines_stats.assert_called_once_with(lab_hash="lab_hash",
                                                    machine_name="test_device",
                                                    all_users=False)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_machines_stats")
def test_get_machine_stats_no_name_no_hash(mock_get_machines_stats, docker_manager):
    with pytest.raises(InvocationError):
        next(docker_manager.get_machine_stats(machine_name="test_device", all_users=True))
    assert not mock_get_machines_stats.called


#
# TESTS: get_links_stats
#
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_stats")
def test_get_links_stats_lab_hash_no_user(mock_get_links_stats, docker_manager):
    docker_manager.get_links_stats(lab_hash="lab_hash", all_users=True)
    mock_get_links_stats.assert_called_once_with(lab_hash="lab_hash", link_name=None, user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_stats")
def test_get_links_stats_lab_name_no_user(mock_get_links_stats, docker_manager):
    docker_manager.get_links_stats(lab_name="lab_name", all_users=True)
    mock_get_links_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"), link_name=None, user=None)


@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_stats")
def test_get_links_stats_no_hash_no_user(mock_get_links_stats, docker_manager):
    docker_manager.get_links_stats(all_users=True)
    mock_get_links_stats.assert_called_once_with(lab_hash=None, link_name=None, user=None)


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_stats")
def test_get_links_stats_no_hash_user(mock_get_links_stats, mock_get_current_user_name, docker_manager):
    mock_get_current_user_name.return_value = "kathara-user"
    docker_manager.get_links_stats()
    mock_get_links_stats.assert_called_once_with(lab_hash=None, link_name=None, user="kathara-user")


@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.manager.docker.DockerLink.DockerLink.get_links_stats")
def test_get_links_stats_lab_hash_user(mock_get_links_stats, mock_get_current_user_name, docker_manager):
    mock_get_current_user_name.return_value = "kathara-user"
    docker_manager.get_links_stats(lab_hash="lab_hash")
    mock_get_links_stats.assert_called_once_with(lab_hash="lab_hash", link_name=None, user="kathara-user")


#
# TESTS: get_link_stats
#
@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_stats")
def test_get_link_stats_lab_hash_no_user(mock_get_links_stats, docker_network, docker_manager):
    mock_get_links_stats.return_value = iter([{"test_network": DockerLinkStats(docker_network)}])
    next(docker_manager.get_link_stats(link_name="test_network", lab_hash="lab_hash", all_users=True))
    mock_get_links_stats.assert_called_once_with(lab_hash="lab_hash", link_name="test_network", all_users=True)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_stats")
def test_get_link_stats_lab_name_no_user(mock_get_links_stats, docker_network, docker_manager):
    mock_get_links_stats.return_value = iter([{"test_network": DockerLinkStats(docker_network)}])
    next(docker_manager.get_link_stats(link_name="test_network", lab_name="lab_name", all_users=True))
    mock_get_links_stats.assert_called_once_with(lab_hash=generate_urlsafe_hash("lab_name"),
                                                 link_name="test_network", all_users=True)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_stats")
def test_get_link_stats_lab_hash_user(mock_get_links_stats, docker_network, docker_manager):
    mock_get_links_stats.return_value = iter([{"test_network": DockerLinkStats(docker_network)}])
    next(docker_manager.get_link_stats(link_name="test_network", lab_hash="lab_hash"))
    mock_get_links_stats.assert_called_once_with(lab_hash="lab_hash", link_name="test_network", all_users=False)


@mock.patch("src.Kathara.manager.docker.DockerManager.DockerManager.get_links_stats")
def test_get_link_stats_no_lab_hash_and_no_name(mock_get_links_stats, docker_network, docker_manager):
    mock_get_links_stats.return_value = iter([{"test_network": DockerLinkStats(docker_network)}])
    with pytest.raises(InvocationError):
        next(docker_manager.get_link_stats(link_name="test_network"))
    assert not mock_get_links_stats.called
