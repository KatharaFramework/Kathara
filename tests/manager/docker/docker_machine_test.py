import sys
from unittest import mock
from unittest.mock import Mock

import docker.types

import pytest

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.manager.docker.DockerMachine import DockerMachine


@pytest.fixture()
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage")
@mock.patch("docker.DockerClient")
def docker_machine(mock_docker_client, mock_docker_image):
    return DockerMachine(mock_docker_client, mock_docker_image)


@pytest.fixture()
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def default_setting(mock_setting):
    return mock_setting


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create(mock_get_current_user_name, mock_setting_get_instance, docker_machine):
    device = Machine(Lab('Default scenario'), "test_device")
    device.add_meta("exec", "ls")
    device.add_meta("mem", "64m")
    device.add_meta("cpus", "2")
    device.add_meta("image", "kathara/test")
    device.add_meta("bridged", False)
    device.add_meta("hosthome_mount", False)
    device.add_meta("shared_mount", False)


    mock_get_current_user_name.return_value = "test-user"
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': False,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash'
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(device)
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network=None,
        network_mode='none',
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.all.forwarding': 1,
                 'net.ipv6.icmp.ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 0,
                 'net.ipv6.conf.all.disable_ipv6': 0},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'}
    )


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_container_name_lab_hash(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = "kathara-user"
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': False,
        'device_prefix': 'dev_prefix'
    })
    mock_setting_get_instance.return_value = setting_mock
    assert "dev_prefix_kathara-user_test_devicelab_hash" == DockerMachine.get_container_name("test_device", "lab_hash")


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_container_name_lab_hash_multiuser(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = "kathara-user"
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'multiuser': True,
        'device_prefix': 'dev_prefix'
    })
    mock_setting_get_instance.return_value = setting_mock
    assert "dev_prefix_test_devicelab_hash" == DockerMachine.get_container_name("test_device", "lab_hash")
