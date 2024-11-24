import sys
from unittest import mock
from unittest.mock import Mock, call

import pytest
from docker.errors import APIError
from requests import Response

sys.path.insert(0, './')

from src.Kathara.manager.docker.exec_stream.DockerExecStream import DockerExecStream
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Link import Link
from src.Kathara.model.Machine import Machine
from src.Kathara.manager.docker.DockerMachine import DockerMachine
from src.Kathara.exceptions import DockerPluginError, MachineBinaryError, PrivilegeError, InvocationError
from src.Kathara.types import SharedCollisionDomainsOption


#
# FIXTURE
#
@pytest.fixture()
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage")
@mock.patch("docker.DockerClient")
def docker_machine(mock_docker_client, mock_docker_image):
    mock_docker_client.version.return_value = {"Version": "27.0.0"}
    return DockerMachine(mock_docker_client, mock_docker_image)


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
    device.api_object.id = "device_id"
    device.api_object.attrs = {"NetworkSettings": {"Networks": {}}}
    device.api_object.labels = {"user": "user", "name": "test_device", "lab_hash": "lab_hash", "shell": "/bin/bash"}
    return device


@pytest.fixture()
@mock.patch("docker.models.containers.Container")
def default_device_b(mock_docker_container):
    device = Machine(Lab('Default scenario'), "test_device_b")
    device.add_meta("image", "kathara/test2")
    device.add_meta("bridged", False)
    device.api_object = mock_docker_container
    device.api_object.id = "device_id"
    device.api_object.attrs = {"NetworkSettings": {"Networks": []}}
    device.api_object.labels = {"user": "user", "name": "test_device_b", "lab_hash": "lab_hash", "shell": "/bin/bash"}
    return device


@pytest.fixture()
@mock.patch("docker.models.containers.Container")
def default_device_c(mock_docker_container):
    device = Machine(Lab('Default scenario'), "test_device_c")
    device.add_meta("image", "kathara/test3")
    device.add_meta("bridged", False)
    device.api_object = mock_docker_container
    device.api_object.id = "device_id"
    device.api_object.attrs = {"NetworkSettings": {"Networks": []}}
    device.api_object.labels = {"user": "user", "name": "test_device_c", "lab_hash": "lab_hash", "shell": "/bin/bash"}
    return device


@pytest.fixture()
def default_link(default_device):
    link = Link(default_device.lab, "A")
    link.api_object = Mock()
    link.api_object.connect = Mock(return_value=True)
    return link


@pytest.fixture()
def default_link_b(default_device):
    link = Link(default_device.lab, "B")
    link.api_object = Mock()
    link.api_object.connect = Mock(return_value=True)
    return link


@pytest.fixture()
def default_link_c(default_device):
    link = Link(default_device.lab, "C")
    link.api_object = Mock()
    link.api_object.connect = Mock(return_value=True)
    return link


#
# TEST: create
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                mock_get_machines_api_objects_by_filters, docker_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network=None,
        network_mode='none',
        networking_config=None,
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 1,
                 'net.ipv6.conf.all.disable_ipv6': 1,
                 'net.ipv6.conf.default.forwarding': 0,
                 'net.ipv6.conf.all.forwarding': 0,
                 },
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )

    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_ipv6(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                     mock_get_machines_api_objects_by_filters, docker_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': True,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network=None,
        network_mode='none',
        networking_config=None,
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.all.forwarding': 1,
                 'net.ipv6.conf.all.accept_ra': 0,
                 'net.ipv6.icmp.ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 0,
                 'net.ipv6.conf.all.disable_ipv6': 0
                 },
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )

    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_privileged(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                           mock_get_machines_api_objects_by_filters, docker_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []

    default_device.lab.add_option("privileged_machines", True)
    mock_get_current_user_name.return_value = "test-user"
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': True,
        "hosthome_mount": False,
        "shared_mount": False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=None,
        privileged=True,
        network=None,
        network_mode='none',
        networking_config=None,
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.all.forwarding': 1,
                 'net.ipv6.conf.all.accept_ra': 0,
                 'net.ipv6.icmp.ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 0,
                 'net.ipv6.conf.all.disable_ipv6': 0},
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )
    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_interface(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                          mock_get_machines_api_objects_by_filters, docker_machine, default_device):
    class LinkApiObj:
        def __init__(self, name):
            self.name = name

    docker_machine._engine_version = "26.0.0"

    link = Link(default_device.lab, "A")
    link.api_object = LinkApiObj("link_a")

    default_device.add_interface(link, 0)

    docker_machine.client.api.create_endpoint_config.return_value = {}
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network="link_a",
        network_mode='bridge',
        networking_config={"link_a": {}},
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 1,
                 'net.ipv6.conf.all.disable_ipv6': 1,
                 'net.ipv6.conf.default.forwarding': 0,
                 'net.ipv6.conf.all.forwarding': 0,
                 },
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )

    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_interface_old_engine(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                                     mock_get_machines_api_objects_by_filters, docker_machine,
                                     default_device):
    class LinkApiObj:
        def __init__(self, name):
            self.name = name

    docker_machine._engine_version = "25.0.0"
    link = Link(default_device.lab, "A")
    link.api_object = LinkApiObj("link_a")

    default_device.add_interface(link, 0)

    docker_machine.client.api.create_endpoint_config.return_value = {}
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network="link_a",
        network_mode='bridge',
        networking_config={"link_a": {}},
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.conf.eth0.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 1,
                 'net.ipv6.conf.all.disable_ipv6': 1,
                 'net.ipv6.conf.default.forwarding': 0,
                 'net.ipv6.conf.all.forwarding': 0,
                 },
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )

    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_interface_mac_addr(mock_get_current_user_name, mock_setting_get_instance,
                                   mock_copy_files, mock_get_machines_api_objects_by_filters, docker_machine,
                                   default_device):
    class LinkApiObj:
        def __init__(self, name):
            self.name = name

    docker_machine._engine_version = "26.0.0"

    link = Link(default_device.lab, "A")
    link.api_object = LinkApiObj("link_a")

    expected_mac_addr = "00:00:00:00:ff:ff"
    iface = default_device.add_interface(link, 0, expected_mac_addr)

    driver_opt = {'kathara.iface': str(iface.num), 'kathara.link': iface.link.name,
                  'kathara.mac_addr': expected_mac_addr}

    docker_machine.client.api.create_endpoint_config.return_value = {'driver_opt': driver_opt}
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)

    docker_machine.client.api.create_endpoint_config.assert_called_once_with(
        driver_opt=driver_opt
    )
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network="link_a",
        network_mode='bridge',
        networking_config={"link_a": {'driver_opt': driver_opt}},
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 1,
                 'net.ipv6.conf.all.disable_ipv6': 1,
                 'net.ipv6.conf.default.forwarding': 0,
                 'net.ipv6.conf.all.forwarding': 0,
                 },
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )

    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_interface_mac_addr_on_old_engine(mock_get_current_user_name, mock_setting_get_instance,
                                                 mock_copy_files, mock_get_machines_api_objects_by_filters,
                                                 docker_machine, default_device):
    class LinkApiObj:
        def __init__(self, name):
            self.name = name

    docker_machine._engine_version = "25.0.0"

    link = Link(default_device.lab, "A")
    link.api_object = LinkApiObj("link_a")

    expected_mac_addr = "00:00:00:00:ff:ff"
    iface = default_device.add_interface(link, 0, expected_mac_addr)

    driver_opt = {'kathara.iface': str(iface.num), 'kathara.link': iface.link.name,
                  'kathara.mac_addr': expected_mac_addr}

    docker_machine.client.api.create_endpoint_config.return_value = {
        'driver_opt': driver_opt
    }
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock
    docker_machine.create(default_device)

    docker_machine.client.api.create_endpoint_config.assert_called_once_with(
        driver_opt=driver_opt
    )
    docker_machine.client.containers.create.assert_called_once_with(
        image='kathara/test',
        name='dev_prefix_test-user_test_device_9pe3y6IDMwx4PfOPu5mbNg',
        hostname='test_device',
        cap_add=['NET_ADMIN', 'NET_RAW', 'NET_BROADCAST', 'NET_BIND_SERVICE', 'SYS_ADMIN'],
        privileged=False,
        network="link_a",
        network_mode='bridge',
        networking_config={"link_a": {'driver_opt': driver_opt}},
        sysctls={'net.ipv4.conf.all.rp_filter': 0,
                 'net.ipv4.conf.default.rp_filter': 0,
                 'net.ipv4.conf.lo.rp_filter': 0,
                 'net.ipv4.conf.eth0.rp_filter': 0,
                 'net.ipv4.ip_forward': 1,
                 'net.ipv4.icmp_ratelimit': 0,
                 'net.ipv6.conf.default.disable_ipv6': 1,
                 'net.ipv6.conf.all.disable_ipv6': 1,
                 'net.ipv6.conf.default.forwarding': 0,
                 'net.ipv6.conf.all.forwarding': 0,
                 },
        environment={},
        mem_limit='64m',
        nano_cpus=2000000000,
        ports=None,
        tty=True,
        stdin_open=True,
        detach=True,
        volumes={},
        labels={'name': 'test_device', 'lab_hash': '9pe3y6IDMwx4PfOPu5mbNg', 'user': 'test-user', 'app': 'kathara',
                'shell': '/bin/bash'},
        ulimits=[]
    )

    assert not mock_copy_files.called


#
# TEST: start
#
def test_start(docker_machine, default_device, default_link, default_link_b):
    # add two interfaces because interace 0 is excluded
    default_device.add_interface(default_link)
    default_device.add_interface(default_link_b)
    default_device.add_meta("num_terms", 3)
    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = ("cmd_stdout", "cmd_stderr")
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    default_device.api_object.start.return_value = True

    docker_machine.start(default_device)

    default_device.api_object.start.assert_called_once()
    docker_machine.client.api.exec_create.assert_called_once()
    docker_machine.client.api.exec_start.assert_called_once()
    docker_machine.client.api.exec_inspect.assert_called_once()
    default_link_b.api_object.connect.assert_called_once()


def test_start_one_mac_addr(docker_machine, default_device, default_link, default_link_b):
    expected_mac_addr = "00:00:00:00:ee:ee"

    default_device.add_interface(default_link)
    iface_b = default_device.add_interface(default_link_b, mac_address=expected_mac_addr)
    default_device.add_meta("num_terms", 3)
    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = ("cmd_stdout", "cmd_stderr")
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    default_device.api_object.start.return_value = True

    docker_machine.start(default_device)

    default_device.api_object.start.assert_called_once()
    docker_machine.client.api.exec_create.assert_called_once()
    docker_machine.client.api.exec_start.assert_called_once()
    docker_machine.client.api.exec_inspect.assert_called_once()
    default_link_b.api_object.connect.assert_called_once_with(
        default_device.api_object,
        driver_opt={
            'kathara.iface': str(iface_b.num), 'kathara.link': iface_b.link.name,
            'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=1',
            'kathara.mac_addr': expected_mac_addr
        }
    )


def test_start_two_mac_addr(docker_machine, default_device, default_link, default_link_b, default_link_c):
    expected_mac_addr_1 = "00:00:00:00:ee:ee"
    expected_mac_addr_2 = "00:00:00:00:ee:ee"

    default_device.add_interface(default_link)
    iface_b = default_device.add_interface(default_link_b, mac_address=expected_mac_addr_1)
    iface_c = default_device.add_interface(default_link_c, mac_address=expected_mac_addr_2)
    default_device.add_meta("num_terms", 3)
    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = ("cmd_stdout", "cmd_stderr")
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    default_device.api_object.start.return_value = True

    docker_machine.start(default_device)

    default_device.api_object.start.assert_called_once()
    docker_machine.client.api.exec_create.assert_called_once()
    docker_machine.client.api.exec_start.assert_called_once()
    docker_machine.client.api.exec_inspect.assert_called_once()
    default_link_b.api_object.connect.assert_called_once_with(
        default_device.api_object,
        driver_opt={
            'kathara.iface': str(iface_b.num), 'kathara.link': iface_b.link.name,
            'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=1',
            'kathara.mac_addr': expected_mac_addr_1
        }
    )
    default_link_c.api_object.connect.assert_called_once_with(
        default_device.api_object,
        driver_opt={
            'kathara.iface': str(iface_c.num), 'kathara.link': iface_c.link.name,
            'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=1',
            'kathara.mac_addr': expected_mac_addr_2
        }
    )


def test_start_plugin_error_endpoint_start(default_device, docker_machine):
    default_device.api_object.start.side_effect = DockerPluginError("endpoint does not exists")
    with pytest.raises(DockerPluginError):
        docker_machine.start(default_device)


def test_start_plugin_error_network_start(default_device, docker_machine):
    default_device.api_object.start.side_effect = DockerPluginError("network does not exists")
    with pytest.raises(DockerPluginError):
        docker_machine.start(default_device)


def test_start_plugin_error_endpoint_connect(default_device, default_link, default_link_b, docker_machine):
    default_device.add_interface(default_link)
    default_device.add_interface(default_link_b)
    default_link_b.api_object.connect.side_effect = DockerPluginError("endpoint does not exists")
    with pytest.raises(DockerPluginError):
        docker_machine.start(default_device)


def test_start_plugin_error_network_connect(default_device, default_link, default_link_b, docker_machine):
    default_device.add_interface(default_link)
    default_device.add_interface(default_link_b)
    default_link_b.api_object.connect.side_effect = DockerPluginError("network does not exists")
    with pytest.raises(DockerPluginError):
        docker_machine.start(default_device)


#
# TEST: _deploy_and_start_machine
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.start")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.create")
def test_deploy_and_start_machine(mock_create, mock_start, docker_machine, default_device):
    machine_item = ("", default_device)
    mock_create.return_value = True
    mock_start.return_value = True
    docker_machine._deploy_and_start_machine(machine_item)
    mock_create.assert_called_once()
    mock_start.assert_called_once()


#
# TEST: deploy_machines
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._deploy_and_start_machine")
def test_deploy_machines(mock_deploy_and_start, mock_setting_get_instance, docker_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "hosthome_mount": False,
        "shared_mount": False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    docker_machine.docker_image.check_from_list.return_value = None
    mock_deploy_and_start.return_value = None
    docker_machine.deploy_machines(lab)
    docker_machine.docker_image.check_from_list.assert_called_once_with({'kathara/test1', 'kathara/test2'})
    assert mock_deploy_and_start.call_count == 2
    mock_deploy_and_start.assert_any_call(('pc1', pc1))
    mock_deploy_and_start.assert_any_call(('pc2', pc2))


@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._deploy_and_start_machine")
def test_deploy_machines_privilege_error(mock_deploy_and_start, mock_setting_get_instance, mock_is_admin,
                                         docker_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "hosthome_mount": False,
        "shared_mount": False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock
    mock_is_admin.return_value = False

    lab = Lab("Default scenario")
    lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    lab.general_options['privileged_machines'] = True
    docker_machine.docker_image.check_from_list.return_value = None
    mock_deploy_and_start.return_value = None

    with pytest.raises(PrivilegeError):
        docker_machine.deploy_machines(lab)

    assert not docker_machine.docker_image.check_from_list.called
    assert not mock_deploy_and_start.called


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._deploy_and_start_machine")
def test_deploy_machines_selected_machines(mock_deploy_and_start, mock_setting_get_instance, docker_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "hosthome_mount": False,
        "shared_mount": False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    docker_machine.docker_image.check_from_list.return_value = None
    mock_deploy_and_start.return_value = None
    docker_machine.deploy_machines(lab, selected_machines={"pc1"})
    docker_machine.docker_image.check_from_list.assert_called_once_with({'kathara/test1'})
    assert mock_deploy_and_start.call_count == 1
    mock_deploy_and_start.assert_any_call(('pc1', pc1))
    assert call(('pc2', pc2)) not in mock_deploy_and_start.mock_calls


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._deploy_and_start_machine")
def test_deploy_machines_excluded_machines(mock_deploy_and_start, mock_setting_get_instance, docker_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "hosthome_mount": False,
        "shared_mount": False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    docker_machine.docker_image.check_from_list.return_value = None
    mock_deploy_and_start.return_value = None
    docker_machine.deploy_machines(lab, excluded_machines={"pc1"})
    docker_machine.docker_image.check_from_list.assert_called_once_with({'kathara/test2'})
    assert mock_deploy_and_start.call_count == 1
    assert call(('pc1', pc1)) not in mock_deploy_and_start.mock_calls
    mock_deploy_and_start.assert_any_call(('pc2', pc2))


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._deploy_and_start_machine")
def test_deploy_machines_selected_and_excluded_machines(mock_deploy_and_start, mock_setting_get_instance,
                                                        docker_machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        "hosthome_mount": False,
        "shared_mount": False,
        'remote_url': None
    })
    mock_setting_get_instance.return_value = setting_mock

    lab = Lab("Default scenario")
    with pytest.raises(InvocationError):
        docker_machine.deploy_machines(lab, selected_machines={"pc1", "pc3"}, excluded_machines={"pc1"})
    assert not docker_machine.docker_image.check_from_list.called
    assert not mock_deploy_and_start.called


#
# TEST: connect_interface
#
def test_connect_interface(docker_machine, default_device, default_link, default_link_b):
    default_device.api_object.attrs["NetworkSettings"] = {}
    default_device.api_object.attrs["NetworkSettings"]["Networks"] = ["A"]
    default_link.api_object.name = "A"

    default_device.add_interface(default_link)
    interface = default_device.add_interface(default_link_b)

    docker_machine.connect_interface(default_device, interface)

    assert not default_link.api_object.connect.called
    default_link_b.api_object.connect.assert_called_once()


def test_connect_interface_mac_addr(docker_machine, default_device, default_link, default_link_b):
    default_device.api_object.attrs["NetworkSettings"] = {}
    default_device.api_object.attrs["NetworkSettings"]["Networks"] = ["A"]
    default_link.api_object.name = "A"

    expected_mac_addr = "00:00:00:00:ff:ff"
    default_device.add_interface(default_link)
    interface = default_device.add_interface(default_link_b, mac_address=expected_mac_addr)

    docker_machine.connect_interface(default_device, interface)

    assert not default_link.api_object.connect.called
    default_link_b.api_object.connect.assert_called_once_with(
        default_device.api_object,
        driver_opt={
            'kathara.iface': str(interface.num), 'kathara.link': interface.link.name,
            'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=1',
            'kathara.mac_addr': expected_mac_addr
        }
    )


def test_connect_interface_plugin_error_network(default_device, default_link, docker_machine):
    interface = default_device.add_interface(default_link)
    response = Response()
    response.status_code = 500
    error = APIError("error",
                     response=response,
                     explanation="network does not exists")
    default_link.api_object.connect.side_effect = error
    with pytest.raises(DockerPluginError):
        docker_machine.connect_interface(default_device, interface)


def test_connect_interface_plugin_error_endpoint(default_device, default_link, docker_machine):
    interface = default_device.add_interface(default_link)
    response = Response()
    response.status_code = 500
    error = APIError("error",
                     response=response,
                     explanation="endpoint does not exists")
    default_link.api_object.connect.side_effect = error
    with pytest.raises(DockerPluginError):
        docker_machine.connect_interface(default_device, interface)


def test_connect_interface_plugin_api_error(default_device, default_link, docker_machine):
    interface = default_device.add_interface(default_link)
    response = Response()
    response.status_code = 510
    error = APIError("error",
                     response=response)
    default_link.api_object.connect.side_effect = error
    with pytest.raises(APIError):
        docker_machine.connect_interface(default_device, interface)


#
# TEST:_create_driver_opt
#
def test_create_driver_opt_no_ipv6(docker_machine, default_device, default_link):
    interface = default_device.add_interface(default_link)
    driver_opt = docker_machine._create_driver_opt(default_device, interface)
    assert driver_opt == {
        'kathara.iface': str(interface.num), 'kathara.link': interface.link.name,
        'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=1',
    }


def test_create_driver_opt_mac_address(docker_machine, default_device, default_link):
    interface = default_device.add_interface(default_link)
    interface.mac_address = '00:00:00:00:00:01'
    driver_opt = docker_machine._create_driver_opt(default_device, interface)
    assert driver_opt == {
        'kathara.iface': str(interface.num), 'kathara.link': interface.link.name,
        'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=1',
        'kathara.mac_addr': '00:00:00:00:00:01'
    }


def test_create_driver_opt_ipv6(docker_machine, default_device, default_link):
    interface = default_device.add_interface(default_link)
    default_device.add_meta('ipv6', True)
    driver_opt = docker_machine._create_driver_opt(default_device, interface)
    assert driver_opt == {
        'kathara.iface': str(interface.num), 'kathara.link': interface.link.name,
        'com.docker.network.endpoint.sysctls': 'net.ipv4.conf.IFNAME.rp_filter=0,net.ipv6.conf.IFNAME.disable_ipv6=0,net.ipv6.conf.IFNAME.forwarding=1',
    }


def test_create_driver_old_docker(docker_machine, default_device, default_link):
    docker_machine._engine_version = '25.0.0'
    interface = default_device.add_interface(default_link)
    driver_opt = docker_machine._create_driver_opt(default_device, interface)
    assert driver_opt == {'kathara.iface': str(interface.num), 'kathara.link': interface.link.name}


#
# TEST: disconnect_from_link
#
def test_disconnect_from_link(docker_machine, default_device, default_link, default_link_b):
    default_device.api_object.attrs["NetworkSettings"] = {}
    default_device.api_object.attrs["NetworkSettings"]["Networks"] = ["A", "B"]
    default_link.api_object.name = "A"
    default_link_b.api_object.name = "B"
    default_device.add_interface(default_link)
    default_device.add_interface(default_link_b)

    docker_machine.disconnect_from_link(default_device, default_link_b)

    assert not default_link.api_object.disconnect.called
    default_link_b.api_object.disconnect.assert_called_once()


#
# TEST: undeploy
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_undeploy_one_device(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine,
                             default_device):
    default_device.api_object.labels = {'name': "test_device"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    mock_undeploy_machine.return_value = None
    docker_machine.undeploy("lab_hash", selected_machines={default_device.name})
    mock_get_machines_api_objects_by_filters.assert_called_once()
    mock_undeploy_machine.assert_called_once_with(default_device.api_object)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_undeploy_three_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine,
                                default_device, default_device_b, default_device_c):
    default_device.api_object.labels = {'name': "test_device"}
    default_device_b.api_object.labels = {'name': "test_device_b"}
    default_device_c.api_object.labels = {'name': "test_device_c"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device_b.api_object, default_device_c.api_object]
    mock_undeploy_machine.return_value = None
    docker_machine.undeploy("lab_hash")
    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 3
    mock_undeploy_machine.assert_any_call(default_device.api_object)
    mock_undeploy_machine.assert_any_call(default_device_b.api_object)
    mock_undeploy_machine.assert_any_call(default_device_c.api_object)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_undeploy_no_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_undeploy_machine.return_value = None
    docker_machine.undeploy("lab_hash")
    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert not mock_undeploy_machine.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_undeploy_selected_machines(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine,
                                    default_device, default_device_b, default_device_c):
    default_device.api_object.labels = {'name': "test_device"}
    default_device_b.api_object.labels = {'name': "test_device_b"}
    default_device_c.api_object.labels = {'name': "test_device_c"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device_b.api_object, default_device_c.api_object]
    mock_undeploy_machine.return_value = None
    docker_machine.undeploy("lab_hash", selected_machines={"test_device"})
    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 1
    mock_undeploy_machine.assert_any_call(default_device.api_object)
    assert call(default_device_b.api_object) not in mock_undeploy_machine.mock_calls
    assert call(default_device_c.api_object) not in mock_undeploy_machine.mock_calls


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_undeploy_excluded_machines(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine,
                                    default_device, default_device_b, default_device_c):
    default_device.api_object.labels = {'name': "test_device"}
    default_device_b.api_object.labels = {'name': "test_device_b"}
    default_device_c.api_object.labels = {'name': "test_device_c"}
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object,
                                                             default_device_b.api_object, default_device_c.api_object]
    mock_undeploy_machine.return_value = None
    docker_machine.undeploy("lab_hash", excluded_machines={"test_device"})
    mock_get_machines_api_objects_by_filters.assert_called_once()
    assert mock_undeploy_machine.call_count == 2
    assert call(default_device.api_object) not in mock_undeploy_machine.mock_calls
    mock_undeploy_machine.assert_any_call(default_device_b.api_object)
    mock_undeploy_machine.assert_any_call(default_device_c.api_object)


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_undeploy_selected_and_excluded_machines(mock_get_machines_api_objects_by_filters, mock_undeploy_machine,
                                                 docker_machine):
    mock_undeploy_machine.return_value = None
    with pytest.raises(InvocationError):
        docker_machine.undeploy(
            "lab_hash", selected_machines={"test_device", "test_device_b"}, excluded_machines={"test_device"}
        )
    assert not mock_get_machines_api_objects_by_filters.called
    assert not mock_undeploy_machine.called


#
# TEST: wipe
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_wipe_one_device(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine,
                         default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    mock_undeploy_machine.return_value = None
    docker_machine.wipe()
    mock_undeploy_machine.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_wipe_no_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_undeploy_machine.return_value = None
    docker_machine.wipe()
    assert not mock_undeploy_machine.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._undeploy_machine")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_wipe_three_devices(mock_get_machines_api_objects_by_filters, mock_undeploy_machine, docker_machine,
                            default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object, default_device.api_object,
                                                             default_device.api_object]
    mock_undeploy_machine.return_value = None
    docker_machine.wipe()
    assert mock_undeploy_machine.call_count == 3


#
# TEST: _undeploy_machine
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine._delete_machine")
def test_undeploy_machine(mock_delete_machine, docker_machine, default_device):
    mock_delete_machine.return_value = None
    docker_machine._undeploy_machine(default_device.api_object)
    mock_delete_machine.assert_called_once()


#
# TEST: exec
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_exec(mock_get_machines_api_objects_by_filters, mock_setting_get_instance, docker_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = iter([("cmd_stdout", "cmd_stderr")])
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    result = docker_machine.exec(default_device.lab.hash, "test_device", "kathara --help", tty=False)
    output = next(result)

    assert output == ('cmd_stdout', 'cmd_stderr')


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_exec_stream(mock_get_machines_api_objects_by_filters, mock_setting_get_instance, docker_machine,
                     default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = iter([("cmd_stdout", "cmd_stderr")])
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    result = docker_machine.exec(
        default_device.lab.hash, "test_device", "kathara --help", stream=True
    )

    assert type(result) == DockerExecStream
    assert result._stream_api_object == "1234"

    output = next(result)

    assert output == ('cmd_stdout', 'cmd_stderr')
    assert result.exit_code() == 0
    docker_machine.client.api.exec_inspect.assert_any_call("1234")


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_exec_stream_error(mock_get_machines_api_objects_by_filters, mock_setting_get_instance, docker_machine,
                           default_device):
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        "device_shell": '/bin/bash',
        'enable_ipv6': False,
        'remote_url': None,
        'hosthome_mount': False,
        'shared_mount': False
    })
    mock_setting_get_instance.return_value = setting_mock

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = iter([("cmd_stdout", "cmd_stderr")])
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 1}
    result = docker_machine.exec(
        default_device.lab.hash, "test_device", "kathara --help", stream=True
    )

    assert type(result) == DockerExecStream
    assert result._stream_api_object == "1234"

    output = next(result)

    assert output == ('cmd_stdout', 'cmd_stderr')
    assert result.exit_code() == 1
    docker_machine.client.api.exec_inspect.assert_any_call("1234")


#
# TEST: _exec_run
#
def test_exec_run_demux(docker_machine, default_device):
    output_iter = ("cmd_stdout", "cmd_stderr")

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_iter
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    result = docker_machine._exec_run(
        default_device.api_object,
        "kathara --help",
        demux=True
    )

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "kathara --help", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=True
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")
    assert result == {'exit_code': 0, 'Id': '1234', 'output': output_iter}


def test_exec_run_demux_stream(docker_machine, default_device):
    output_gen = map(lambda x: x, [("cmd_stdout", "cmd_stderr")])

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_gen
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": None}
    result = docker_machine._exec_run(
        default_device.api_object,
        "kathara --help",
        stream=True,
        demux=True
    )

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "kathara --help", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=True, socket=False, demux=True
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")
    assert result == {'exit_code': None, 'Id': '1234', 'output': output_gen}


def test_exec_run_oci_runtime_error_1_no_demux(docker_machine, default_device):
    output_str = b"OCI runtime exec failed: exec failed: unable to start container process: exec: \"exe\": " \
                 b"executable file not found in $PATH: unknown"

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_str
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 126}

    with pytest.raises(MachineBinaryError) as e:
        docker_machine._exec_run(
            default_device.api_object,
            "exe",
        )

        assert e.binary == "exe"

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "exe", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=False
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")


def test_exec_run_oci_runtime_error_1_demux(docker_machine, default_device):
    output_str = (b"OCI runtime exec failed: exec failed: unable to start container process: exec: \"exe\": "
                  b"executable file not found in $PATH: unknown", b"")

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_str
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 126}

    with pytest.raises(MachineBinaryError) as e:
        docker_machine._exec_run(
            default_device.api_object,
            "exe",
            demux=True
        )

        assert e.binary == "exe"

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "exe", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=True
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")


def test_exec_run_oci_runtime_error_1_stream(docker_machine, default_device):
    output_gen = map(lambda x: x, [b"OCI runtime exec failed: exec failed: unable to start container process: "
                                   b"exec: \"exe\": executable file not found in $PATH: unknown"])

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_gen
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": None}

    result = docker_machine._exec_run(
        default_device.api_object,
        "exe",
        demux=True
    )

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "exe", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=True
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")
    assert result == {'exit_code': None, 'Id': '1234', 'output': output_gen}


def test_exec_run_oci_runtime_error_2_no_demux(docker_machine, default_device):
    output_str = b"OCI runtime exec failed: exec failed: unable to start container process: exec: \"exe1\": " \
                 b"stat exe1: no such file or directory: unknown"

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_str
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 126}

    with pytest.raises(MachineBinaryError) as e:
        docker_machine._exec_run(
            default_device.api_object,
            "exe1",
        )

        assert e.binary == "exe1"

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "exe1", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=False
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")


def test_exec_run_oci_runtime_error_2_demux(docker_machine, default_device):
    output_str = (b"OCI runtime exec failed: exec failed: unable to start container process: exec: \"exe1\": " \
                  b"stat exe1: no such file or directory: unknown", b"")

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_str
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 126}

    with pytest.raises(MachineBinaryError) as e:
        docker_machine._exec_run(
            default_device.api_object,
            "exe1",
            demux=True
        )

        assert e.binary == "exe1"

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "exe1", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=True
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")


def test_exec_run_oci_runtime_error_2_stream(docker_machine, default_device):
    output_gen = map(lambda x: x, [b"OCI runtime exec failed: exec failed: unable to start container process: "
                                   b"exec: \"exe1\": stat exe1: no such file or directory: unknown"])

    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = output_gen
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": None}

    result = docker_machine._exec_run(
        default_device.api_object,
        "exe1",
        demux=True
    )

    docker_machine.client.api.exec_create.assert_called_once_with(
        default_device.api_object.id, "exe1", stdout=True, stderr=True, stdin=False, tty=False,
        privileged=False, user='', environment=None, workdir=None
    )
    docker_machine.client.api.exec_start.assert_called_once_with(
        "1234", detach=False, tty=False, stream=False, socket=False, demux=True
    )
    docker_machine.client.api.exec_inspect.assert_called_once_with("1234")
    assert result == {'exit_code': None, 'Id': '1234', 'output': output_gen}


#
# TEST: get_machines_api_objects
#
def test_get_machines_api_objects_by_filters(docker_machine):
    docker_machine.client.containers.list.return_value = ["test_device"]
    docker_machine.get_machines_api_objects_by_filters("lab_hash_value", "test_device", "user_name_value")
    filters = {"label": ["app=kathara", "user=user_name_value", "lab_hash=lab_hash_value", "name=test_device"]}
    docker_machine.client.containers.list.assert_called_once_with(all=True, filters=filters, ignore_removed=True)


def test_get_machines_api_objects_by_filters_empty_filters(docker_machine):
    docker_machine.client.containers.list.return_value = None
    docker_machine.get_machines_api_objects_by_filters()
    filters = {"label": ["app=kathara"]}
    docker_machine.client.containers.list.assert_called_once_with(all=True, filters=filters, ignore_removed=True)


def test_get_machines_api_objects_by_filters_lab_hash_filter(docker_machine):
    docker_machine.client.containers.list.return_value = None
    docker_machine.get_machines_api_objects_by_filters("lab_hash_value", None, None)
    filters = {"label": ["app=kathara", "lab_hash=lab_hash_value"]}
    docker_machine.client.containers.list.assert_called_once_with(all=True, filters=filters, ignore_removed=True)


def test_get_machines_api_objects_by_filters_lab_device_name_filter(docker_machine):
    docker_machine.client.containers.list.return_value = ["test_device"]
    docker_machine.get_machines_api_objects_by_filters(None, "test_device", None)
    filters = {"label": ["app=kathara", "name=test_device"]}
    docker_machine.client.containers.list.assert_called_once_with(all=True, filters=filters, ignore_removed=True)


def test_get_machines_api_objects_by_filters_user_filter(docker_machine):
    docker_machine.client.containers.list.return_value = None
    docker_machine.get_machines_api_objects_by_filters(None, None, "user_name_value")
    filters = {"label": ["app=kathara", "user=user_name_value"]}
    docker_machine.client.containers.list.assert_called_once_with(all=True, filters=filters, ignore_removed=True)


#
# TEST: get_container_name
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_container_name_lab_hash(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = "kathara-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix'
    })
    mock_setting_get_instance.return_value = setting_mock

    assert "dev_prefix_kathara-user_test_device_lab_hash" == DockerMachine.get_container_name("test_device", "lab_hash")


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_container_name_lab_hash_shared_cd_lab(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = "kathara-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cd': SharedCollisionDomainsOption.LABS,
        'device_prefix': 'dev_prefix'
    })
    mock_setting_get_instance.return_value = setting_mock


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_get_container_name_lab_hash_shared_cd_user(mock_get_current_user_name, mock_setting_get_instance):
    mock_get_current_user_name.return_value = "kathara-user"

    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cd': SharedCollisionDomainsOption.USERS,
        'device_prefix': 'dev_prefix'
    })
    mock_setting_get_instance.return_value = setting_mock


#
# TEST: delete_machine
#
def test_delete_machine_running(docker_machine, default_device):
    docker_machine.client.api.exec_create.return_value = {"Id": "1234"}
    docker_machine.client.api.exec_start.return_value = ("cmd_stdout", "cmd_stderr")
    docker_machine.client.api.exec_inspect.return_value = {"ExitCode": 0}
    default_device.api_object.remove.return_value = None
    default_device.api_object.status = "running"

    docker_machine._delete_machine(default_device.api_object)
    docker_machine.client.api.exec_create.assert_called_once()
    docker_machine.client.api.exec_start.assert_called_once()
    docker_machine.client.api.exec_inspect.assert_called_once()
    default_device.api_object.remove.assert_called_once_with(v=True, force=True)


def test_delete_machine_not_running(docker_machine, default_device):
    default_device.api_object.exec_run.return_value = None
    default_device.api_object.remove.return_value = None
    default_device.api_object.status = "stop"

    docker_machine._delete_machine(default_device.api_object)
    assert not default_device.api_object.exec_run.called
    default_device.api_object.remove.assert_called_once_with(v=True, force=True)


#
# TEST: get_machines_stats
#
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash(mock_get_machines_api_objects_by_filters, docker_machine, default_device):
    default_device.api_object.name = "test_device"
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    default_device.api_object.stats.return_value = iter([{'pids_stats': {}, 'cpu_stats': {}, 'memory_stats': {}}])
    next(docker_machine.get_machines_stats(lab_hash="lab_hash", user='user'))

    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", machine_name=None,
                                                                     user='user')
    default_device.api_object.stats.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_device_name(mock_get_machines_api_objects_by_filters, docker_machine,
                                                 default_device):
    default_device.api_object.name = "test_device"
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    default_device.api_object.stats.return_value = iter([{'pids_stats': {}, 'cpu_stats': {}, 'memory_stats': {}}])
    next(docker_machine.get_machines_stats(lab_hash="lab_hash", machine_name="test_device", user="user"))

    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", machine_name="test_device",
                                                                     user="user")
    default_device.api_object.stats.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_device_name_user(mock_get_machines_api_objects_by_filters, docker_machine,
                                                      default_device):
    default_device.api_object.name = "test_device"
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    default_device.api_object.stats.return_value = iter([{'pids_stats': {}, 'cpu_stats': {}, 'memory_stats': {}}])
    next(docker_machine.get_machines_stats(lab_hash="lab_hash", machine_name="test_device", user="user"))

    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", machine_name="test_device",
                                                                     user="user")
    default_device.api_object.stats.assert_called_once()


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_device_not_found(mock_get_machines_api_objects_by_filters, docker_machine,
                                                      default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    assert next(docker_machine.get_machines_stats(lab_hash="lab_hash", user="user")) == {}

    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", machine_name=None,
                                                                     user="user")
    assert not default_device.api_object.stats.called


@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_and_name_device_not_found(mock_get_machines_api_objects_by_filters, docker_machine,
                                                               default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    assert next(docker_machine.get_machines_stats(lab_hash="lab_hash", machine_name="test_device", user="user")) == {}
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", machine_name="test_device",
                                                                     user="user")
    assert not default_device.api_object.stats.called


@mock.patch("src.Kathara.utils.is_admin")
@mock.patch("src.Kathara.manager.docker.DockerMachine.DockerMachine.get_machines_api_objects_by_filters")
def test_get_machines_stats_lab_hash_no_user(mock_get_machines_api_objects_by_filters, mock_is_admin, docker_machine,
                                             default_device):
    default_device.api_object.name = "test_device"
    mock_get_machines_api_objects_by_filters.return_value = [default_device.api_object]
    mock_is_admin.return_value = True
    default_device.api_object.stats.return_value = iter([{'pids_stats': {}, 'cpu_stats': {}, 'memory_stats': {}}])
    next(docker_machine.get_machines_stats(lab_hash="lab_hash", user=None))
    mock_get_machines_api_objects_by_filters.assert_called_once_with(lab_hash="lab_hash", machine_name=None,
                                                                     user=None)
    default_device.api_object.stats.assert_called_once()


@mock.patch("src.Kathara.utils.is_admin")
def test_get_machines_stats_privilege_error(mock_is_admin, docker_machine):
    mock_is_admin.return_value = False
    with pytest.raises(PrivilegeError):
        next(docker_machine.get_machines_stats(lab_hash="lab_hash", machine_name="test_device", user=None))
