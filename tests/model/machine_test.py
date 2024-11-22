import sys
from unittest import mock
from unittest.mock import Mock

import pytest

from src.Kathara.exceptions import MachineCollisionDomainError

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Link import Link
from src.Kathara.exceptions import MachineOptionError, NonSequentialMachineInterfaceError

sys.path.insert(0, './src')


@pytest.fixture()
def default_device():
    return Machine(Lab("test_lab"), "test_machine")


def test_default_device_parameters(default_device: Machine):
    assert default_device.name == "test_machine"
    assert len(default_device.interfaces) == 0
    assert default_device.meta == {
        'exec_commands': [],
        'sysctls': {},
        'envs': {},
        'ports': {},
        'ulimits': {}
    }
    assert default_device.api_object is None
    assert default_device.fs is None
    assert not default_device.lab.has_host_path()


#
# TEST: add_interface
#
def test_add_interface(default_device: Machine):
    interface = default_device.add_interface(Link(default_device.lab, "A"))
    assert len(default_device.interfaces) == 1
    assert default_device.interfaces[0].link.name == "A"
    assert interface == default_device.interfaces[0]


def test_add_interface_with_number(default_device: Machine):
    interface = default_device.add_interface(Link(default_device.lab, "A"), number=2)
    assert len(default_device.interfaces) == 1
    assert default_device.interfaces[2].link.name == "A"
    assert interface == default_device.interfaces[2]


def test_add_interface_with_mac_address(default_device: Machine):
    interface = default_device.add_interface(Link(default_device.lab, "A"), mac_address="00:00:00:00:00:01")
    assert len(default_device.interfaces) == 1
    assert default_device.interfaces[0].link.name == "A"
    assert interface == default_device.interfaces[0]
    assert interface.mac_address == "00:00:00:00:00:01"


def test_add_interface_with_number_and_mac_address(default_device: Machine):
    interface = default_device.add_interface(Link(default_device.lab, "A"),
                                             number=2, mac_address="00:00:00:00:00:01")
    assert len(default_device.interfaces) == 1
    assert default_device.interfaces[2].link.name == "A"
    assert interface == default_device.interfaces[2]
    assert interface.mac_address == "00:00:00:00:00:01"


def test_add_interface_exception(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"))
    with pytest.raises(MachineCollisionDomainError):
        default_device.add_interface(Link(default_device.lab, "B"), number=0)


def test_add_two_interfaces_on_same_cd(default_device: Machine):
    link = Link(default_device.lab, "A")

    default_device.add_interface(link)
    with pytest.raises(MachineCollisionDomainError):
        default_device.add_interface(link)


#
# TEST: remove_interface
#
def test_remove_interface(default_device: Machine):
    link = Link(default_device.lab, "A")
    default_device.add_interface(link)
    assert len(default_device.interfaces) == 1
    assert default_device.interfaces[0].link.name == "A"
    assert default_device.name in link.machines
    default_device.remove_interface(link)
    assert len(default_device.interfaces) == 1
    assert len(link.machines.keys()) == 0
    assert default_device.interfaces[0] is None


def test_remove_interface_one(default_device: Machine):
    link_a = Link(default_device.lab, "A")
    link_b = Link(default_device.lab, "B")
    link_c = Link(default_device.lab, "C")
    default_device.add_interface(link_a)
    default_device.add_interface(link_b)
    default_device.add_interface(link_c)
    assert len(default_device.interfaces) == 3
    assert default_device.interfaces[0].link.name == "A"
    assert default_device.interfaces[1].link.name == "B"
    assert default_device.interfaces[2].link.name == "C"
    default_device.remove_interface(link_a)
    assert len(default_device.interfaces) == 3
    assert default_device.interfaces[0] is None
    assert default_device.interfaces[1].link.name == "B"
    assert default_device.interfaces[2].link.name == "C"
    assert default_device.name not in link_a.machines


def test_remove_interface_exception(default_device: Machine):
    link = Link(default_device.lab, "A")
    with pytest.raises(MachineCollisionDomainError):
        default_device.remove_interface(link)


def test_add_remove_add_interface(default_device: Machine):
    link = Link(default_device.lab, "A")
    default_device.add_interface(link)
    default_device.remove_interface(link)
    interface = default_device.add_interface(link)
    assert default_device.interfaces[1] == interface


def test_add_remove_three_interfaces(default_device: Machine):
    link_a = Link(default_device.lab, "A")
    link_b = Link(default_device.lab, "B")
    link_c = Link(default_device.lab, "C")
    link_d = Link(default_device.lab, "D")

    default_device.add_interface(link_a)
    default_device.add_interface(link_b)
    default_device.add_interface(link_c)

    default_device.remove_interface(link_c)

    interface = default_device.add_interface(link_d)
    assert default_device.interfaces[3] == interface


#
# TEST: add_meta
#
def test_add_meta_sysctl(default_device: Machine):
    default_device.add_meta("sysctl", "net.ipv4.tcp_syncookies=1")
    assert default_device.meta['sysctls']['net.ipv4.tcp_syncookies'] == 1


def test_add_meta_sysctl_not_net_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("sysctl", "kernel.shm_rmid_forced=1")


def test_add_meta_sysctl_not_format_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("sysctl", "kernel.shm_rmid_forced")


def test_add_meta_sysctl_non_numeric(default_device: Machine):
    default_device.add_meta("sysctl", "net.test_sysctl.text=test")
    assert default_device.meta['sysctls']['net.test_sysctl.text'] == "test"


def test_add_meta_sysctl_negative_number(default_device: Machine):
    default_device.add_meta("sysctl", "net.test_sysctl.negative=-1")
    assert default_device.meta['sysctls']['net.test_sysctl.negative'] == -1


def test_add_meta_sysctl_negative_number_not_format(default_device: Machine):
    default_device.add_meta("sysctl", "net.test_sysctl.negative=-1-")
    assert default_device.meta['sysctls']['net.test_sysctl.negative'] == "-1-"


def test_add_meta_sysctl_with_spaces(default_device: Machine):
    default_device.add_meta("sysctl", "net.ipv4.tcp_rmem=4096 87380 33554432")
    assert default_device.meta['sysctls']['net.ipv4.tcp_rmem'] == "4096 87380 33554432"


def test_add_meta_sysctl_double_equal(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("sysctl", "net.test_sysctl.text=test=again")


def test_add_meta_env(default_device: Machine):
    default_device.add_meta("env", "MY_ENV_VAR=test")
    assert default_device.meta['envs']['MY_ENV_VAR'] == "test"


def test_add_meta_env_number(default_device: Machine):
    default_device.add_meta("env", "MY_ENV_VAR=1")
    assert default_device.meta['envs']['MY_ENV_VAR'] == "1"


def test_add_meta_env_with_spaces(default_device: Machine):
    default_device.add_meta("env", "MY_ENV_VAR=spaced value")
    assert default_device.meta['envs']['MY_ENV_VAR'] == "spaced value"


def test_add_meta_env_double_equal(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("env", "MY_ENV_VAR=test=not valid")


def test_add_meta_env_not_format_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("env", "MY_ENV_VAR")


def test_add_meta_port_only_guest(default_device: Machine):
    default_device.add_meta("port", "8080")
    assert default_device.meta['ports'][(3000, "tcp")] == 8080


def test_add_meta_port_guest_protocol(default_device: Machine):
    default_device.add_meta("port", "8080/udp")
    assert default_device.meta['ports'][(3000, "udp")] == 8080


def test_add_meta_port_host_guest_protocol(default_device: Machine):
    default_device.add_meta("port", "2000:8080/udp")
    assert default_device.meta['ports'][(2000, "udp")] == 8080


def test_add_meta_port_protocol_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("port", "8080/ppp")


def test_add_meta_port_format_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("port", ":2000")


def test_add_meta_port_format_exception2(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("port", ":2000")


def test_add_meta_overwrite(default_device: Machine):
    result = default_device.add_meta("test_meta", "test_value")
    assert "test_meta" in default_device.meta
    assert default_device.meta["test_meta"] == "test_value"
    assert result is None
    result = default_device.add_meta("test_meta", "test_new_value")
    assert "test_meta" in default_device.meta
    assert default_device.meta["test_meta"] == "test_new_value"
    assert result == "test_value"


def test_add_meta_overwrite_sysctl(default_device: Machine):
    result = default_device.add_meta("sysctl", "net.test.a=1")
    assert default_device.meta["sysctls"]["net.test.a"] == 1
    assert result is None
    result = default_device.add_meta("sysctl", "net.test.a=2")
    assert default_device.meta["sysctls"]["net.test.a"] == 2
    assert result == 1


def test_add_meta_overwrite_env(default_device: Machine):
    result = default_device.add_meta("env", "TEST_ENV=abc")
    assert default_device.meta["envs"]["TEST_ENV"] == "abc"
    assert result is None
    result = default_device.add_meta("env", "TEST_ENV=def")
    assert default_device.meta["envs"]["TEST_ENV"] == "def"
    assert result == "abc"


def test_add_meta_overwrite_port(default_device: Machine):
    result = default_device.add_meta("port", "3000:4000")
    assert default_device.meta["ports"][(3000, "tcp")] == 4000
    assert result is None
    result = default_device.add_meta("port", "3000:5000")
    assert default_device.meta["ports"][(3000, "tcp")] == 5000
    assert result == 4000


def test_add_meta_ulimit(default_device):
    default_device.add_meta("ulimit", "nofile=1024:2048")
    assert default_device.meta['ulimits']['nofile'] == {'soft': 1024, 'hard': 2048}


def test_add_meta_ulimit_soft_only(default_device):
    default_device.add_meta("ulimit", "nofile=1024")
    assert default_device.meta['ulimits']['nofile'] == {'soft': 1024, 'hard': 1024}


def test_add_meta_ulimit_negative_value(default_device):
    default_device.add_meta("ulimit", "memlock=-1")
    assert default_device.meta['ulimits']['memlock'] == {'soft': -1, 'hard': -1}


def test_add_meta_ulimit_invalid_format(default_device):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("ulimit", "nofile=1024:2048:4096")


def test_add_meta_ulimit_not_format_exception(default_device):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("ulimit", "nofile1024")


def test_add_meta_ulimit_soft_greater_than_hard(default_device):
    default_device.add_meta("ulimit", "nofile=2048:1024")
    assert default_device.meta['ulimits']['nofile'] == {'soft': 1024, 'hard': 1024}


def test_add_meta_ulimit_soft_unlimited_hard_limited(default_device):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("ulimit", "nofile=-1:1024")


def test_add_meta_ulimit_soft_limited_hard_unlimited(default_device):
    default_device.add_meta("ulimit", "nofile=2048:-1")
    assert default_device.meta['ulimits']['nofile'] == {'soft': 2048, 'hard': -1}


def test_add_meta_ulimit_soft_and_hard_unlimited(default_device):
    default_device.add_meta("ulimit", "nofile=-1:-1")
    assert default_device.meta['ulimits']['nofile'] == {'soft': -1, 'hard': -1}


def test_add_meta_ulimit_invalid_value(default_device):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("ulimit", "nofile=1024:-2")


#
# TEST: check
#
def test_check(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"), number=0)
    default_device.add_interface(Link(default_device.lab, "B"), number=1)
    default_device.check()


def test_check_exception(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"), number=2)
    default_device.add_interface(Link(default_device.lab, "B"), number=4)
    with pytest.raises(NonSequentialMachineInterfaceError):
        default_device.check()


#
# TEST: get_image
#
@mock.patch("src.Kathara.setting.Setting.Setting.get_instance")
def test_get_image_default(mock_setting_get_instance, default_device: Machine):
    setting_mock = Mock()
    setting_mock.configure_mock(**{
        'image': "kathara/frr"
    })
    mock_setting_get_instance.return_value = setting_mock

    assert default_device.get_image() == "kathara/frr"


def test_get_image():
    kwargs = {'image': 'kathara/frr'}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_image() == "kathara/frr"


#
# TEST: get_mem
#
def test_get_mem_default(default_device: Machine):
    assert default_device.get_mem() is None


def test_get_mem_from_lab_options():
    lab = Lab('mem_test')
    lab.add_global_machine_metadata("mem", "150m")
    device = Machine(lab, "test_machine")
    assert device.get_mem() == "150m"


def test_get_mem_from_device_meta():
    kwargs = {"mem": "200m"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_mem() == "200m"


#
# TEST: get_cpu
#
def test_get_cpu_default(default_device: Machine):
    assert default_device.get_cpu() is None


def test_get_cpu_from_lab_options():
    lab = Lab('mem_test')
    lab.add_global_machine_metadata("cpus", "2")
    device = Machine(lab, "test_machine")
    assert device.get_cpu() == 2


def test_get_cpu_from_device_meta():
    kwargs = {"cpus": "1"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_cpu() == 1


#
# TEST: num_terms
#
def test_get_num_terms_default(default_device: Machine):
    assert default_device.get_num_terms() == 1


def test_get_num_terms_from_lab_options():
    lab = Lab('mem_test')
    lab.add_global_machine_metadata("num_terms", "2")
    device = Machine(lab, "test_machine")
    assert device.get_num_terms() == 2


def test_get_num_terms_from_device_meta():
    kwargs = {"num_terms": "1"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_num_terms() == 1


def test_get_num_terms_mix():
    # Lab options have a greater priority than machine options
    lab = Lab('mem_test')
    lab.add_global_machine_metadata("num_terms", "2")
    kwargs = {"num_terms": "1"}
    device1 = Machine(lab, "test_machine1", **kwargs)
    device2 = Machine(lab, "test_machine2")
    assert device1.get_num_terms() == 2
    assert device2.get_num_terms() == 2


#
# TEST: is_ipv6_enabled
#
def test_is_ipv6_enabled_from_lab_options():
    lab = Lab('mem_test')
    lab.add_global_machine_metadata("ipv6", True)
    device = Machine(lab, "test_machine")
    assert device.is_ipv6_enabled()


def test_is_ipv6_enabled_from_device_meta_bool():
    kwargs = {"ipv6": True}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.is_ipv6_enabled()


def test_is_ipv6_enabled_from_device_meta_str():
    kwargs = {"ipv6": "True"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.is_ipv6_enabled()


def test_is_ipv6_enabled_mix():
    # Lab options have a greater priority than machine options
    lab = Lab('mem_test')
    lab.add_global_machine_metadata("ipv6", False)
    kwargs = {"ipv6": True}
    device1 = Machine(lab, "test_machine1", **kwargs)
    device2 = Machine(lab, "test_machine2")
    assert not device1.is_ipv6_enabled()
    assert not device2.is_ipv6_enabled()
