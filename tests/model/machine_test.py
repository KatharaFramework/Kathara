import pytest
import sys

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.model.Machine import Machine
from src.Kathara.model.Link import Link


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
