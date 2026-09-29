import sys

sys.path.insert(0, './')

from src.Kathara.model.Lab import Lab
from src.Kathara.model.LabSerializer import lab_to_dict, lab_from_dict, SAVE_FORMAT_VERSION


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
