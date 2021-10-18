import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara import utils
from tempfile import mkdtemp
from src.Kathara.exceptions import MachineOptionError


@pytest.fixture()
def default_scenario():
    return Lab("default_scenario")


@pytest.fixture()
def temporary_path():
    return mkdtemp("kathara_test")


@pytest.fixture()
def directory_scenario(temporary_path):
    Path(os.path.join(temporary_path, "shared.startup")).touch()
    Path(os.path.join(temporary_path, "shared.shutdown")).touch()
    return Lab("directory_scenario", path=temporary_path)


def test_default_scenario_creation(default_scenario: Lab):
    assert default_scenario.name == "default_scenario"
    assert default_scenario.description is None
    assert default_scenario.version is None
    assert default_scenario.author is None
    assert default_scenario.email is None
    assert default_scenario.web is None
    assert default_scenario.machines == {}
    assert default_scenario.links == {}
    assert default_scenario.general_options == {}
    assert not default_scenario.has_dependencies
    assert default_scenario.path is None
    assert default_scenario.shared_shutdown_path is None
    assert default_scenario.shared_startup_path is None
    assert default_scenario.shared_folder is None
    assert default_scenario.hash == utils.generate_urlsafe_hash(default_scenario.name)


def test_directory_scenario_creation_no_shared_files(directory_scenario: Lab, temporary_path: str):
    assert directory_scenario.name == "directory_scenario"
    assert directory_scenario.description is None
    assert directory_scenario.version is None
    assert directory_scenario.author is None
    assert directory_scenario.email is None
    assert directory_scenario.web is None
    assert directory_scenario.machines == {}
    assert directory_scenario.links == {}
    assert directory_scenario.general_options == {}
    assert not directory_scenario.has_dependencies
    assert directory_scenario.path == temporary_path
    assert directory_scenario.shared_shutdown_path == os.path.join(temporary_path, 'shared.shutdown')
    assert directory_scenario.shared_startup_path == os.path.join(temporary_path, 'shared.startup')
    assert directory_scenario.shared_folder is None
    assert directory_scenario.hash == utils.generate_urlsafe_hash(temporary_path)


def test_get_or_new_machine_not_exist(default_scenario: Lab):
    default_scenario.get_or_new_machine("pc1")
    assert len(default_scenario.machines) == 1
    assert default_scenario.machines['pc1']


def test_get_or_new_machine_exists(default_scenario: Lab):
    default_scenario.get_or_new_machine("pc1")
    default_scenario.get_or_new_machine("pc1")
    assert len(default_scenario.machines) == 1
    assert default_scenario.machines['pc1']


def test_get_or_new_machine_two_devices(default_scenario: Lab):
    default_scenario.get_or_new_machine("pc1")
    default_scenario.get_or_new_machine("pc2")
    assert len(default_scenario.machines) == 2
    assert default_scenario.machines['pc1']
    assert default_scenario.machines['pc2']


def test_get_or_new_link_not_exists(default_scenario: Lab):
    default_scenario.get_or_new_link("A")
    assert len(default_scenario.links) == 1
    assert default_scenario.links['A']


def test_get_or_new_link_exists(default_scenario: Lab):
    default_scenario.get_or_new_link("A")
    default_scenario.get_or_new_link("A")
    assert len(default_scenario.links) == 1
    assert default_scenario.links['A']


def test_get_or_new_link_two_cd(default_scenario: Lab):
    default_scenario.get_or_new_link("A")
    default_scenario.get_or_new_link("B")
    assert len(default_scenario.links) == 2
    assert default_scenario.links['A']
    assert default_scenario.links['B']


def test_connect_one_machine_to_link(default_scenario: Lab):
    default_scenario.connect_machine_to_link("pc1", "A")
    assert len(default_scenario.machines) == 1
    assert default_scenario.machines['pc1']
    assert len(default_scenario.links) == 1
    assert default_scenario.links['A']
    assert default_scenario.machines['pc1'].interfaces[0].name == 'A'


def test_connect_two_machine_to_link(default_scenario: Lab):
    default_scenario.connect_machine_to_link("pc1", "A")
    assert len(default_scenario.machines) == 1
    assert default_scenario.machines['pc1']
    assert len(default_scenario.links) == 1
    assert default_scenario.links['A']
    default_scenario.connect_machine_to_link("pc2", "A")
    assert len(default_scenario.machines) == 2
    assert default_scenario.machines['pc2']
    assert len(default_scenario.links) == 1
    assert default_scenario.links['A']
    assert default_scenario.machines['pc1'].interfaces[0].name == 'A'
    assert default_scenario.machines['pc2'].interfaces[0].name == 'A'


def test_connect_machine_to_two_links(default_scenario: Lab):
    default_scenario.connect_machine_to_link("pc1", "A")
    default_scenario.connect_machine_to_link("pc1", "B")
    assert len(default_scenario.machines) == 1
    assert default_scenario.machines['pc1']
    assert len(default_scenario.links) == 2
    assert default_scenario.links['A']
    assert default_scenario.links['B']
    assert default_scenario.machines['pc1'].interfaces[0].name == 'A'
    assert default_scenario.machines['pc1'].interfaces[1].name == 'B'


def test_assign_meta_to_machine(default_scenario: Lab):
    default_scenario.get_or_new_machine("pc1")
    default_scenario.assign_meta_to_machine("pc1", "test_meta", "test_value")
    assert "test_meta" in default_scenario.machines['pc1'].meta
    assert default_scenario.machines['pc1'].meta["test_meta"] == "test_value"


def test_assign_meta_to_machine_exception(default_scenario: Lab):
    default_scenario.get_or_new_machine("pc1")
    with pytest.raises(MachineOptionError):
        default_scenario.assign_meta_to_machine("pc1", "port", "value")


def test_intersect_machines(default_scenario: Lab):
    default_scenario.connect_machine_to_link("pc1", "A")
    default_scenario.connect_machine_to_link("pc2", "A")
    default_scenario.connect_machine_to_link("pc2", "B")
    assert len(default_scenario.machines) == 2
    links = default_scenario.get_links_from_machines(selected_machines=["pc1"])
    assert len(default_scenario.machines) == 2
    assert 'pc1' in default_scenario.machines
    assert 'pc2' in default_scenario.machines
    assert 'A' in links
    assert 'B' not in links


def test_create_shared_folder(directory_scenario: Lab):
    directory_scenario.create_shared_folder()
    assert os.path.isdir(os.path.join(directory_scenario.path, 'shared'))


def test_create_shared_folder_no_path(default_scenario: Lab):
    assert default_scenario.create_shared_folder() is None


def test_apply_dependencies(default_scenario: Lab):
    default_scenario.get_or_new_machine("pc1")
    default_scenario.get_or_new_machine("pc2")
    default_scenario.get_or_new_machine("pc3")

    default_scenario.apply_dependencies(["pc3", "pc1", "pc2"])

    assert default_scenario.machines.popitem()[0] == "pc2"
    assert default_scenario.machines.popitem()[0] == "pc1"
    assert default_scenario.machines.popitem()[0] == "pc3"
