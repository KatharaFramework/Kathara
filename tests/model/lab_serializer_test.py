import sys

sys.path.insert(0, './')

import pytest

from src.Kathara.exceptions import LinkModeError, InterfaceVlanError
from src.Kathara.model.Lab import Lab
from src.Kathara.model.LabSerializer import lab_to_dict, lab_from_dict, SAVE_FORMAT_VERSION
from src.Kathara.types import LinkMode


def _build_lab():
    lab = Lab("Default scenario")
    lab.description = "a description"
    lab.version = "1.0"
    lab.author = "tester"

    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc1.add_meta("mem", "128M")
    pc1.add_meta("port", "8080:80/tcp")
    pc1.add_meta("sysctl", "net.ipv4.ip_forward=1")
    pc1.add_meta("env", "FOO=bar")

    lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})

    lab.connect_machine_to_link(pc1.name, "A", mac_address="00:11:22:33:44:55")
    lab.connect_machine_to_link(pc1.name, "B")
    lab.connect_machine_to_link("pc2", "A")

    return lab


def test_lab_to_dict_structure():
    lab = _build_lab()
    data = lab_to_dict(lab)

    assert data["save_format_version"] == SAVE_FORMAT_VERSION
    assert data["lab"]["name"] == "Default scenario"
    assert data["lab"]["hash"] == lab.hash
    assert data["lab"]["description"] == "a description"
    assert {m["name"] for m in data["machines"]} == {"pc1", "pc2"}
    assert {link["name"] for link in data["links"]} == {"A", "B"}

    pc1 = next(m for m in data["machines"] if m["name"] == "pc1")
    # ports tuple-key is converted to a JSON-safe list of objects
    assert pc1["meta"]["ports"] == [{"host_port": 8080, "protocol": "tcp", "guest_port": 80}]
    assert pc1["meta"]["image"] == "kathara/test1"
    assert {i["link"] for i in pc1["interfaces"]} == {"A", "B"}


def test_lab_to_dict_is_json_serializable():
    import json
    json.dumps(lab_to_dict(_build_lab()))


def test_round_trip_preserves_topology_and_metas():
    lab = _build_lab()

    restored = lab_from_dict(lab_to_dict(lab))

    assert restored.name == lab.name
    assert restored.hash == lab.hash
    assert restored.description == lab.description
    assert set(restored.machines.keys()) == {"pc1", "pc2"}
    assert set(restored.links.keys()) == {"A", "B"}

    pc1 = restored.get_machine("pc1")
    assert pc1.meta["image"] == "kathara/test1"
    assert pc1.meta["mem"] == "128M"
    assert pc1.meta["ports"] == {(8080, "tcp"): 80}
    assert pc1.meta["sysctls"] == {"net.ipv4.ip_forward": 1}
    assert pc1.meta["envs"] == {"FOO": "bar"}

    assert list(pc1.interfaces.keys()) == [0, 1]
    assert pc1.interfaces[0].link.name == "A"
    assert pc1.interfaces[0].mac_address == "00:11:22:33:44:55"
    assert pc1.interfaces[1].link.name == "B"


def test_round_trip_drops_non_restorable_metas():
    lab = Lab("scenario")
    pc1 = lab.get_or_new_machine("pc1")
    pc1.add_meta("exec", "echo hi")

    data = lab_to_dict(lab)
    assert "exec_commands" not in data["machines"][0]["meta"]

    restored = lab_from_dict(data)
    # default (empty) value is restored
    assert restored.get_machine("pc1").meta["exec_commands"] == []


def test_lab_from_dict_with_no_name():
    # A scenario saved from a directory without LAB_NAME has a null name but a valid hash.
    data = {
        "save_format_version": SAVE_FORMAT_VERSION,
        "lab": {"name": None, "hash": "somehash", "general_options": {}, "global_machine_metadata": {}},
        "machines": [{"name": "pc1", "meta": {}, "interfaces": []}],
        "links": [],
    }

    restored = lab_from_dict(data)
    assert restored.name is None
    assert restored.hash == "somehash"
    assert set(restored.machines.keys()) == {"pc1"}


def test_lab_from_dict_preserves_hash_not_derivable_from_name():
    # Emulate a scenario reconstructed from a hash only (name not matching the hash).
    data = {
        "save_format_version": SAVE_FORMAT_VERSION,
        "lab": {"name": "reconstructed_lab", "hash": "a-custom-hash", "general_options": {},
                "global_machine_metadata": {}},
        "machines": [{"name": "pc1", "meta": {}, "interfaces": []}],
        "links": [],
    }

    restored = lab_from_dict(data)
    assert restored.hash == "a-custom-hash"


def _build_lab_with_modes():
    lab = Lab("Default scenario")
    lab.new_link("A", mode="managed")
    lab.new_link("B", mode=LinkMode.SWITCH)
    lab.new_link("C", mode="hub")

    lab.connect_machine_to_link("pc1", "A", vlan=10)
    lab.connect_machine_to_link("pc2", "A", mac_address="00:11:22:33:44:55", vlan=20, tagged_vlans=[40, 30])
    lab.connect_machine_to_link("r1", "A", tagged_vlans=[10, 20])
    lab.connect_machine_to_link("r1", "B")
    lab.connect_machine_to_link("r1", "C")
    lab.connect_machine_to_link("r1", "D")

    return lab


def test_lab_to_dict_modes_and_vlans():
    import json

    data = lab_to_dict(_build_lab_with_modes())
    # The modes are written as plain strings
    data = json.loads(json.dumps(data))

    assert {link["name"]: link["mode"] for link in data["links"]} == {
        "A": "managed", "B": "switch", "C": "hub", "D": None
    }

    interfaces = {
        (machine["name"], interface["number"]): interface
        for machine in data["machines"] for interface in machine["interfaces"]
    }
    assert (interfaces[("pc1", 0)]["vlan"], interfaces[("pc1", 0)]["tagged_vlans"]) == (10, [])
    assert (interfaces[("pc2", 0)]["vlan"], interfaces[("pc2", 0)]["tagged_vlans"]) == (20, [30, 40])
    assert (interfaces[("r1", 0)]["vlan"], interfaces[("r1", 0)]["tagged_vlans"]) == (None, [10, 20])
    assert (interfaces[("r1", 1)]["vlan"], interfaces[("r1", 1)]["tagged_vlans"]) == (None, [])


def test_round_trip_preserves_modes_and_vlans():
    lab = _build_lab_with_modes()

    restored = lab_from_dict(lab_to_dict(lab))

    assert restored.get_link("A").mode == LinkMode.MANAGED
    assert restored.get_link("A").is_managed()
    assert restored.get_link("B").mode == LinkMode.SWITCH
    assert restored.get_link("C").mode == LinkMode.HUB
    assert restored.get_link("D").mode is None

    pc2 = restored.get_machine("pc2").interfaces[0]
    assert (pc2.mac_address, pc2.vlan, pc2.tagged_vlans) == ("00:11:22:33:44:55", 20, [30, 40])
    assert restored.get_machine("pc1").interfaces[0].vlan == 10
    r1 = restored.get_machine("r1")
    assert (r1.interfaces[0].vlan, r1.interfaces[0].tagged_vlans) == (None, [10, 20])
    assert not r1.interfaces[1].has_vlans()

    # The restored network scenario can be deployed: the VLANs are on a managed collision domain
    restored.check_integrity()
    # And it is saved as it was
    assert lab_to_dict(restored) == lab_to_dict(lab)


def test_lab_from_dict_without_modes_and_vlans():
    # A manifest written before the collision domain modes existed.
    data = {
        "save_format_version": SAVE_FORMAT_VERSION,
        "lab": {"name": "scenario", "hash": "somehash", "general_options": {}, "global_machine_metadata": {}},
        "machines": [{"name": "pc1", "meta": {},
                      "interfaces": [{"number": 0, "link": "A", "mac_address": None}]}],
        "links": [{"name": "A"}, {"name": "B"}],
    }

    restored = lab_from_dict(data)

    assert restored.get_link("A").mode is None
    assert restored.get_link("B").mode is None
    interface = restored.get_machine("pc1").interfaces[0]
    assert interface.vlan is None
    assert interface.tagged_vlans == []
    assert not interface.has_vlans()


def test_lab_from_dict_invalid_mode_error():
    data = lab_to_dict(_build_lab_with_modes())
    data["links"][0]["mode"] = "router"

    with pytest.raises(LinkModeError):
        lab_from_dict(data)


def test_lab_from_dict_invalid_vlan_error():
    data = lab_to_dict(_build_lab_with_modes())
    data["machines"][0]["interfaces"][0]["vlan"] = 5000

    with pytest.raises(InterfaceVlanError):
        lab_from_dict(data)
