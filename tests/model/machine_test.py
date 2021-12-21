import os
import sys
import tarfile
from unittest import mock
from unittest.mock import Mock

import pytest

from src.Kathara.exceptions import MachineCollisionDomainConflictError

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
        'sysctls': {},
        'bridged': False,
        'ports': {}
    }
    assert len(default_device.startup_commands) == 0
    assert default_device.api_object is None
    assert default_device.capabilities == ["NET_ADMIN", "NET_RAW", "NET_BROADCAST", "NET_BIND_SERVICE", "SYS_ADMIN"]
    assert default_device.startup_path is None
    assert default_device.shutdown_path is None
    assert default_device.folder is None
    assert not default_device.lab.has_path()


def test_add_interface(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"))
    assert len(default_device.interfaces) == 1
    assert default_device.interfaces[0].name == "A"


def test_add_interface_exception(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"))
    with pytest.raises(Exception):
        default_device.add_interface(Link(default_device.lab, "B"), number=0)


def test_add_two_interfaces_on_same_cd(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"))
    with pytest.raises(MachineCollisionDomainConflictError):
        default_device.add_interface(Link(default_device.lab, "A"))


def test_add_meta_sysctl(default_device: Machine):
    default_device.add_meta("sysctl", "net.ipv4.tcp_syncookies=1")
    assert default_device.meta['sysctls']['net.ipv4.tcp_syncookies'] == 1


def test_add_meta_sysctl_not_net_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("sysctl", "kernel.shm_rmid_forced=1")


def test_add_meta_sysctl_not_format_exception(default_device: Machine):
    with pytest.raises(MachineOptionError):
        default_device.add_meta("sysctl", "kernel.shm_rmid_forced")


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


def test_check(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"), number=0)
    default_device.add_interface(Link(default_device.lab, "B"), number=1)
    default_device.check()


def test_check_exception(default_device: Machine):
    default_device.add_interface(Link(default_device.lab, "A"), number=2)
    default_device.add_interface(Link(default_device.lab, "B"), number=4)
    with pytest.raises(NonSequentialMachineInterfaceError):
        default_device.check()


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


def test_get_mem_default(default_device: Machine):
    assert default_device.get_mem() is None


def test_get_mem_from_lab_options():
    lab = Lab('mem_test')
    lab.add_option("mem", "150m")
    device = Machine(lab, "test_machine")
    assert device.get_mem() == "150m"


def test_get_mem_from_device_meta():
    kwargs = {"mem": "200m"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_mem() == "200m"


def test_get_cpu_default(default_device: Machine):
    assert default_device.get_cpu() is None


def test_get_cpu_from_lab_options():
    lab = Lab('mem_test')
    lab.add_option("cpus", "2")
    device = Machine(lab, "test_machine")
    assert device.get_cpu() == 2


def test_get_cpu_from_device_meta():
    kwargs = {"cpus": "1"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_cpu() == 1


def test_get_num_terms_default(default_device: Machine):
    assert default_device.get_num_terms() == 1


def test_get_num_terms_from_lab_options():
    lab = Lab('mem_test')
    lab.add_option("num_terms", "2")
    device = Machine(lab, "test_machine")
    assert device.get_num_terms() == 2


def test_get_num_terms_from_device_meta():
    kwargs = {"num_terms": "1"}
    device = Machine(Lab("test_lab"), "test_machine", **kwargs)
    assert device.get_num_terms() == 1


def test_get_num_terms_mix():
    # Lab options have a greater priority than machine options
    lab = Lab('mem_test')
    lab.add_option("num_terms", "2")
    kwargs = {"num_terms": "1"}
    device1 = Machine(lab, "test_machine1", **kwargs)
    device2 = Machine(lab, "test_machine2")
    assert device1.get_num_terms() == 2
    assert device2.get_num_terms() == 2


@mock.patch("src.Kathara.utils.pack_file_for_tar")
def test_pack_data_hidden_files(pack_file_for_tar_mock):
    lab_path = os.path.join("tests", "model", "hiddenfiles")
    lab = Lab(None, lab_path)
    device = lab.get_or_new_machine("test_machine")

    pack_file_for_tar_mock.return_value = (tarfile.TarInfo(""), None)

    device.pack_data()

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, ".hidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "nothidden"),
        arc_name="hostlab/" + os.path.join(device.name, "nothidden")
    )

    assert pack_file_for_tar_mock.call_count == 2


@mock.patch("src.Kathara.utils.pack_file_for_tar")
def test_pack_data_hidden_files_recursive(pack_file_for_tar_mock):
    lab_path = os.path.join("tests", "model", "hiddenfilesrecursive")
    lab = Lab(None, lab_path)
    device = lab.get_or_new_machine("test_machine")

    pack_file_for_tar_mock.return_value = (tarfile.TarInfo(""), None)

    device.pack_data()

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, ".hidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "nothidden"),
        arc_name="hostlab/" + os.path.join(device.name, "nothidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "etc", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, "etc", ".hidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "etc", "nothidden"),
        arc_name="hostlab/" + os.path.join(device.name, "etc", "nothidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "etc", "log", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, "etc", "log", ".hidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "etc", "log", "nothidden"),
        arc_name="hostlab/" + os.path.join(device.name, "etc", "log", "nothidden")
    )

    assert pack_file_for_tar_mock.call_count == 6


@mock.patch("src.Kathara.utils.pack_file_for_tar")
def test_pack_data_only_hidden_files(pack_file_for_tar_mock):
    lab_path = os.path.join("tests", "model", "hiddenfilesonly")
    lab = Lab(None, lab_path)
    device = lab.get_or_new_machine("test_machine")

    pack_file_for_tar_mock.return_value = (tarfile.TarInfo(""), None)

    device.pack_data()

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, ".hidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "etc", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, "etc", ".hidden")
    )

    pack_file_for_tar_mock.assert_any_call(
        os.path.join(lab_path, "test_machine", "etc", "log", ".hidden"),
        arc_name="hostlab/" + os.path.join(device.name, "etc", "log", ".hidden")
    )

    assert pack_file_for_tar_mock.call_count == 3
