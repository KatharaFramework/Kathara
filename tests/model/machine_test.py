import pytest
import sys

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Link import Link
from src.Kathara.exceptions import MachineOptionError, NonSequentialMachineInterfaceError

sys.path.insert(0, './src')
from Kathara.setting.Setting import Setting


@pytest.fixture()
def default_device():
    return Machine(Lab("Machine_test_lab"), "test_machine")


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


def test_get_image_default():
    old_image = Setting.get_instance().image
    Setting.get_instance().image = "kathara/frr"
    Setting.get_instance().save()
    pc = Machine(Lab("Machine_test_lab"), "test_machine")
    assert pc.get_image() == "kathara/frr"
    Setting.get_instance().image = old_image
    Setting.get_instance().save()


def test_get_image():
    kwargs = {'image': 'kathara/frr'}
    pc = Machine(Lab("Machine_test_lab"), "test_machine", **kwargs)
    assert pc.get_image() == "kathara/frr"


def test_get_mem_default(default_device: Machine):
    assert default_device.get_mem() is None


def test_get_mem_from_lab_options():
    lab = Lab('mem_test')
    lab.add_option("mem", "150m")
    pc = Machine(lab, "test_machine")
    assert pc.get_mem() == "150m"


def test_get_mem_from_device_meta():
    kwargs = {"mem": "200m"}
    pc = Machine(Lab("Machine_test_lab"), "test_machine", **kwargs)
    assert pc.get_mem() == "200m"


def test_get_cpu_default(default_device: Machine):
    assert default_device.get_cpu() is None


def test_get_cpu_from_lab_options():
    lab = Lab('mem_test')
    lab.add_option("cpus", "2")
    pc = Machine(lab, "test_machine")
    assert pc.get_cpu() == 2


def test_get_cpu_from_device_meta():
    kwargs = {"cpus": "1"}
    pc = Machine(Lab("Machine_test_lab"), "test_machine", **kwargs)
    assert pc.get_cpu() == 1


def test_get_num_terms_default(default_device: Machine):
    assert default_device.get_num_terms() == 1


def test_get_num_terms_from_lab_options():
    lab = Lab('mem_test')
    lab.add_option("num_terms", "2")
    pc = Machine(lab, "test_machine")
    assert pc.get_num_terms() == 2


def test_get_num_terms_from_device_meta():
    kwargs = {"num_terms": "1"}
    pc = Machine(Lab("Machine_test_lab"), "test_machine", **kwargs)
    assert pc.get_num_terms() == 1


def test_get_num_terms_mix():
    # Lab options have a greater priority than machine options
    lab = Lab('mem_test')
    lab.add_option("num_terms", "2")
    kwargs = {"num_terms": "1"}
    pc1 = Machine(lab, "test_machine1", **kwargs)
    pc2 = Machine(lab, "test_machine2")
    assert pc1.get_num_terms() == 2
    assert pc2.get_num_terms() == 2
