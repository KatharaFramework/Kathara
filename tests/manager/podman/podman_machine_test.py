import sys
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.podman.PodmanMachine import PodmanMachine, CPU_PERIOD, IFACE_SYSCTL_RE, \
    IFACE_ALIAS_PREFIX, build_iface_alias, parse_iface_alias, get_container_ifaces
from src.Kathara.model.Lab import Lab
from src.Kathara.model.Link import Link
from src.Kathara.model.Machine import Machine
from podman.errors import APIError

from src.Kathara.exceptions import MachineOptionError, NotSupportedError
from src.Kathara.types import SharedCollisionDomainsOption


#
# FIXTURE
#
@pytest.fixture()
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage")
@mock.patch("podman.PodmanClient")
def podman_machine(mock_podman_client, mock_podman_image):
    return PodmanMachine(mock_podman_client, mock_podman_image)


@pytest.fixture()
@mock.patch("podman.domain.containers.Container")
def default_device(mock_podman_container):
    device = Machine(Lab('Default scenario'), "test_device")
    device.add_meta("mem", "64m")
    device.add_meta("cpus", "2")
    device.add_meta("image", "kathara/test")
    device.add_meta("bridged", False)
    device.api_object = mock_podman_container
    device.api_object.id = "device_id"
    device.api_object.attrs = {"NetworkSettings": {"Networks": {}}}
    device.api_object.labels = {"user": "user", "name": "test_device", "lab_hash": "lab_hash", "shell": "/bin/bash"}
    return device


@pytest.fixture()
def default_link(default_device):
    link = Link(default_device.lab, "A")
    link.api_object = Mock()
    link.api_object.name = "podman_link_a"
    link.api_object.connect = Mock(return_value=True)
    return link


def _setting_mock(**overrides):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'shared_cds': SharedCollisionDomainsOption.NOT_SHARED,
        'device_prefix': 'dev_prefix',
        'device_shell': '/bin/bash',
        'enable_ipv6': False,
        'hosthome_mount': False,
        'shared_mount': False,
        **overrides
    })
    return setting_mock


#
# TEST: create
#
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_no_interfaces(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                              mock_get_machines_api_objects_by_filters, podman_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock()

    podman_machine.create(default_device)

    _, kwargs = podman_machine.client.containers.create.call_args
    assert kwargs['image'] == 'kathara/test'
    assert kwargs['hostname'] == 'test_device'
    assert kwargs['privileged'] is False
    assert kwargs['network_mode'] == 'none'
    assert 'networks' not in kwargs
    # No container-level MAC address kwarg: MACs are set per-interface (see `_get_network_options` /
    # `connect_interface`), not through podman-py's `containers.create(mac_address=...)`.
    assert 'mac_address' not in kwargs
    assert kwargs['mem_limit'] == '64m'
    # cpus=2 -> cpu_quota = 2 * CPU_PERIOD, and cpu_period must be set alongside it
    assert kwargs['cpu_quota'] == 2 * CPU_PERIOD
    assert kwargs['cpu_period'] == CPU_PERIOD
    assert kwargs['ports'] == {}
    assert kwargs['volumes'] == {}
    # Anonymous-volume fix: both declared VOLUME paths must be tmpfs-mounted since nothing else covers them.
    mount_targets = {m['target'] for m in kwargs['mounts']}
    assert mount_targets == {'/hosthome', '/shared'}
    assert all(m['type'] == 'tmpfs' for m in kwargs['mounts'])
    assert kwargs['ulimits'] == []
    assert kwargs['entrypoint'] is None
    assert kwargs['command'] is None
    assert kwargs['labels']['name'] == 'test_device'
    assert kwargs['labels']['user'] == 'test-user'
    assert kwargs['labels']['app'] == 'kathara'

    assert not mock_copy_files.called


@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_with_first_interface(mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
                                     mock_get_machines_api_objects_by_filters, podman_machine, default_device,
                                     default_link):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock()

    default_device.add_interface(default_link, mac_address="00:00:00:00:00:01")

    podman_machine.create(default_device)

    _, kwargs = podman_machine.client.containers.create.call_args
    # libpod requires an explicit `bridge` netns mode when `networks` carry per-network options
    # such as a static MAC address (`networks=` and `network_mode="none"` are mutually exclusive).
    assert kwargs['network_mode'] == 'bridge'
    # The interface name, static MAC and per-interface sysctls (prefixed for the Kathará network
    # plugin) travel as per-network options, not as container-level kwargs.
    assert kwargs['networks'] == {
        'podman_link_a': {
            'interface_name': 'eth0',
            'aliases': ['kathara-eth0'],
            'static_mac': '00:00:00:00:00:01',
            'options': {
                'sysctl.net.ipv4.conf.eth0.rp_filter': '0',
                'sysctl.net.ipv6.conf.eth0.disable_ipv6': '1',
            }
        }
    }
    assert 'mac_address' not in kwargs
    # `sysctls=` only carries device-wide sysctls: per-interface ones are filtered out (they went
    # into the network options above instead).
    assert kwargs['sysctls']['net.ipv4.conf.all.rp_filter'] == '0'
    assert kwargs['sysctls']['net.ipv4.ip_forward'] == '1'
    assert all(not IFACE_SYSCTL_RE.match(k) for k in kwargs['sysctls'])
    # Sysctl values must all be strings for the Podman API.
    assert all(isinstance(v, str) for v in kwargs['sysctls'].values())


@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_first_interface_custom_sysctl_in_network_options_not_in_sysctls(
        mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
        mock_get_machines_api_objects_by_filters, podman_machine, default_device, default_link):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock()

    # A user override for eth0's rp_filter (per-interface) and a device-wide sysctl.
    default_device.add_meta("sysctl", "net.ipv4.conf.eth0.rp_filter=1")
    default_device.add_meta("sysctl", "net.ipv4.tcp_syncookies=1")
    default_device.add_interface(default_link, number=0)

    podman_machine.create(default_device)

    _, kwargs = podman_machine.client.containers.create.call_args
    # The per-interface override lands in eth0's network options, with the user value...
    assert kwargs['networks']['podman_link_a']['options']['sysctl.net.ipv4.conf.eth0.rp_filter'] == '1'
    # ...and never in the device-wide sysctls, which still carry the unrelated device-wide sysctl.
    assert 'net.ipv4.conf.eth0.rp_filter' not in kwargs['sysctls']
    assert kwargs['sysctls']['net.ipv4.tcp_syncookies'] == '1'
    assert all(not IFACE_SYSCTL_RE.match(k) for k in kwargs['sysctls'])


#
# TEST: SELinux mount labeling
#
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_shared_mount_only_keeps_selinux_confinement(
        mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
        mock_get_machines_api_objects_by_filters, podman_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock(shared_mount=True)
    default_device.lab.shared_path = "/tmp/shared"

    podman_machine.create(default_device)

    _, kwargs = podman_machine.client.containers.create.call_args
    assert kwargs['volumes']["/tmp/shared"] == {'bind': '/shared', 'mode': 'rw', 'extended_mode': ['z']}
    assert 'security_opt' not in kwargs


@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.copy_files")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
@mock.patch("src.Kathara.utils.get_current_user_home")
def test_create_hosthome_mount_disables_selinux_label(
        mock_get_current_user_home, mock_get_current_user_name, mock_setting_get_instance, mock_copy_files,
        mock_get_machines_api_objects_by_filters, podman_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_get_current_user_home.return_value = "/home/test-user"
    mock_setting_get_instance.return_value = _setting_mock(hosthome_mount=True)

    podman_machine.create(default_device)

    _, kwargs = podman_machine.client.containers.create.call_args
    assert kwargs['volumes']["/home/test-user"] == {'bind': '/hosthome', 'mode': 'rw'}
    assert kwargs['security_opt'] == ["disable"]


@mock.patch("src.Kathara.manager.podman.PodmanMachine.PodmanMachine.get_machines_api_objects_by_filters")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
@mock.patch("src.Kathara.utils.get_current_user_name")
def test_create_privileged_not_supported(mock_get_current_user_name, mock_setting_get_instance,
                                         mock_get_machines_api_objects_by_filters, podman_machine, default_device):
    mock_get_machines_api_objects_by_filters.return_value = []
    mock_get_current_user_name.return_value = "test-user"
    mock_setting_get_instance.return_value = _setting_mock()

    default_device.add_meta("privileged", True)

    with pytest.raises(NotSupportedError, match="Privileged devices"):
        podman_machine.create(default_device)

    assert not podman_machine.client.containers.create.called


#
# TEST: connect_interface / disconnect_from_link
#
@mock.patch("src.Kathara.manager.podman.libpod_compat.LibpodCompat.network_connect")
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_connect_interface(mock_setting_get_instance, mock_network_connect, podman_machine, default_device,
                           default_link):
    mock_setting_get_instance.return_value = _setting_mock()
    default_device.api_object.attrs = {"NetworkSettings": {"Networks": {}}}
    interface = default_device.add_interface(default_link, number=0)

    podman_machine.connect_interface(default_device, interface)

    # Hot-connect goes through the libpod compat layer (podman-py's native `Network.connect()` cannot
    # set interface name, static MAC or per-interface sysctls), applying the same per-interface
    # sysctls computed for a first-interface connection at create time.
    mock_network_connect.assert_called_once_with(
        default_link.api_object, default_device.api_object, "eth0",
        mac_address=interface.mac_address,
        sysctls={
            "net.ipv4.conf.eth0.rp_filter": 0,
            "net.ipv6.conf.eth0.disable_ipv6": 1,
        },
        aliases=["kathara-eth0"],
    )


@mock.patch("src.Kathara.manager.podman.libpod_compat.LibpodCompat.network_connect")
def test_connect_interface_already_attached(mock_network_connect, podman_machine, default_device, default_link):
    default_device.api_object.attrs = {"NetworkSettings": {"Networks": {"podman_link_a": {}}}}
    interface = default_device.add_interface(default_link, number=0)

    podman_machine.connect_interface(default_device, interface)

    assert not mock_network_connect.called


def test_disconnect_from_link(default_device, default_link):
    default_device.api_object.attrs = {"NetworkSettings": {"Networks": {"podman_link_a": {}}}}

    PodmanMachine.disconnect_from_link(default_device, default_link)

    default_link.api_object.disconnect.assert_called_once_with(default_device.api_object)


#
# TEST: get_machines_stats
#
def test_get_machines_stats_all_users_not_supported(podman_machine):
    machines_stats = podman_machine.get_machines_stats()

    with pytest.raises(NotSupportedError, match="Statistics of all users"):
        next(machines_stats)


#
# TEST: get_container_name
#
def test_get_container_name():
    with mock.patch("src.Kathara.setting.Setting.Setting.get_instance") as mock_setting_get_instance, \
            mock.patch("src.Kathara.utils.get_current_user_name") as mock_get_current_user_name:
        mock_setting_get_instance.return_value = _setting_mock()
        mock_get_current_user_name.return_value = "test-user"

        name = PodmanMachine.get_container_name("pc1", "lab_hash")
        assert name == "dev_prefix_test-user_pc1_lab_hash"


#
# TEST: build_iface_alias / parse_iface_alias
#
def test_build_iface_alias():
    assert build_iface_alias(0) == "kathara-eth0"
    assert build_iface_alias(12) == "kathara-eth12"


def test_parse_iface_alias_valid():
    assert parse_iface_alias("kathara-eth0") == 0
    assert parse_iface_alias("kathara-eth12") == 12


def test_parse_iface_alias_invalid():
    assert parse_iface_alias("eth0") is None
    assert parse_iface_alias("kathara-eth") is None
    assert parse_iface_alias("some-other-alias") is None
    assert parse_iface_alias("kathara-eth1x") is None
    assert parse_iface_alias(f"{IFACE_ALIAS_PREFIX}-1") is None


#
# TEST: _get_network_options
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_network_options_includes_alias(mock_setting_get_instance, podman_machine, default_device, default_link):
    mock_setting_get_instance.return_value = _setting_mock()
    interface = default_device.add_interface(default_link, mac_address="00:00:00:00:00:09", number=3)

    options = podman_machine._get_network_options(default_device, interface)

    assert options["interface_name"] == "eth3"
    assert options["aliases"] == ["kathara-eth3"]
    assert options["static_mac"] == "00:00:00:00:00:09"


@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_network_options_alias_without_mac(mock_setting_get_instance, podman_machine, default_device,
                                                default_link):
    mock_setting_get_instance.return_value = _setting_mock()
    interface = default_device.add_interface(default_link, number=0)

    options = podman_machine._get_network_options(default_device, interface)

    assert options["aliases"] == ["kathara-eth0"]
    assert "static_mac" not in options


#
# TEST: get_container_ifaces
#
def _kathara_network_mock(link_name):
    network = Mock()
    network.attrs = {"labels": {"name": link_name}}
    return network


def test_get_container_ifaces_three_networks_one_non_kathara():
    container = Mock()
    container.attrs = {
        "NetworkSettings": {
            "Networks": {
                "podman_link_a": {"Aliases": ["kathara-eth0"], "MacAddress": "00:00:00:00:00:01"},
                "podman_link_b": {"Aliases": ["kathara-eth1"], "MacAddress": "00:00:00:00:00:02"},
                # Not a Kathará network (e.g. the default Podman bridge used for bridged devices):
                # absent from `networks_by_name`, so it must be skipped even though it has an alias.
                "podman": {"Aliases": ["kathara-eth2"], "MacAddress": "00:00:00:00:00:03"},
            }
        }
    }
    networks_by_name = {
        "podman_link_a": _kathara_network_mock("A"),
        "podman_link_b": _kathara_network_mock("B"),
    }

    ifaces = get_container_ifaces(container, networks_by_name)

    assert set(ifaces.keys()) == {"A", "B"}
    assert ifaces["A"]["num"] == 0
    assert ifaces["A"]["mac_address"] == "00:00:00:00:00:01"
    assert ifaces["A"]["network"] is networks_by_name["podman_link_a"]
    assert ifaces["B"]["num"] == 1
    assert ifaces["B"]["mac_address"] == "00:00:00:00:00:02"


def test_get_container_ifaces_skips_network_without_kathara_alias():
    container = Mock()
    container.attrs = {
        "NetworkSettings": {
            "Networks": {
                "podman_link_a": {"Aliases": [], "MacAddress": "00:00:00:00:00:01"},
                "podman_link_b": {"Aliases": ["some-other-alias"], "MacAddress": "00:00:00:00:00:02"},
            }
        }
    }
    networks_by_name = {
        "podman_link_a": _kathara_network_mock("A"),
        "podman_link_b": _kathara_network_mock("B"),
    }

    assert get_container_ifaces(container, networks_by_name) == {}


def test_get_container_ifaces_skips_network_without_name_label():
    container = Mock()
    container.attrs = {
        "NetworkSettings": {
            "Networks": {
                "podman_link_a": {"Aliases": ["kathara-eth0"], "MacAddress": "00:00:00:00:00:01"},
            }
        }
    }
    unlabeled_network = Mock()
    unlabeled_network.attrs = {"labels": {}}

    assert get_container_ifaces(container, {"podman_link_a": unlabeled_network}) == {}


#
# TEST: start errors caused by rootless limits
#
# Messages returned by libpod on Podman 5.8.7.
SETRLIMIT_EXPLANATION = "crun: setrlimit `RLIMIT_NOFILE`: Operation not permitted: OCI permission denied"
ROOTLESSPORT_EXPLANATION = (
    "rootlessport cannot expose privileged port 80, you can add 'net.ipv4.ip_unprivileged_port_start=80' to "
    "/etc/sysctl.conf (currently 1024), or choose a larger port number (>= 1024): "
    "listen tcp 0.0.0.0:80: bind: permission denied"
)


def test_translate_start_error_setrlimit(default_device):
    default_device.add_meta("ulimit", "nofile=1024:524289")
    error = APIError("500 Server Error", explanation=SETRLIMIT_EXPLANATION)

    result = PodmanMachine._translate_start_error(default_device, error)

    assert isinstance(result, MachineOptionError)
    assert "`nofile`" in str(result)
    assert "soft=1024, hard=524289" in str(result)
    assert "`test_device`" in str(result)


def test_translate_start_error_privileged_port(default_device):
    error = APIError("500 Server Error", explanation=ROOTLESSPORT_EXPLANATION)

    result = PodmanMachine._translate_start_error(default_device, error)

    assert isinstance(result, MachineOptionError)
    assert "`test_device`" in str(result)
    assert "ip_unprivileged_port_start" in str(result)


def test_translate_start_error_other_errors_unchanged(default_device):
    error = APIError("500 Server Error", explanation="some other libpod failure")

    assert PodmanMachine._translate_start_error(default_device, error) is error


def test_start_failure_removes_device_and_raises_translated_error(podman_machine, default_device):
    default_device.add_meta("ulimit", "nofile=1024:524289")
    default_device.api_object.start.side_effect = APIError("500 Server Error", explanation=SETRLIMIT_EXPLANATION)

    with pytest.raises(MachineOptionError) as excinfo:
        podman_machine.start(default_device)

    default_device.api_object.remove.assert_called_once_with(force=True)
    assert isinstance(excinfo.value.__cause__, APIError)


def test_start_failure_remove_error_keeps_original_error(podman_machine, default_device):
    default_device.api_object.start.side_effect = APIError("500 Server Error", explanation="some other libpod failure")
    default_device.api_object.remove.side_effect = APIError("remove failed")

    with pytest.raises(APIError) as excinfo:
        podman_machine.start(default_device)

    assert excinfo.value.explanation == "some other libpod failure"
