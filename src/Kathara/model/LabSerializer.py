from typing import Dict, Any, List

from .Lab import Lab
from .Machine import Machine

# Version of the manifest format produced by `lab_to_dict`. Bump it on breaking changes.
SAVE_FORMAT_VERSION: int = 1

# Device meta keys that cannot be faithfully reconstructed and must not be serialized.
# Mirrors the note in `DockerManager.get_lab_from_api`: "exec", "ipv6" and "num_terms" cannot be rebuilt.
_NON_RESTORABLE_META: List[str] = ["exec_commands", "num_terms", "ipv6"]


def lab_to_dict(lab: Lab) -> Dict[str, Any]:
    """Serialize a network scenario topology into a JSON-safe dictionary (the save manifest).

    This captures the network structure (devices, collision domains, interfaces) and the device
    configuration (`Machine.meta`), but NOT the container filesystem/runtime state (which is
    persisted separately as committed images by the manager).

    Args:
        lab (Kathara.model.Lab.Lab): The network scenario to serialize.

    Returns:
        Dict[str, Any]: A JSON-serializable dictionary representing the network scenario.
    """
    machines = []
    for machine in lab.machines.values():
        interfaces = [
            {
                "number": number,
                "link": interface.link.name,
                "mac_address": interface.mac_address,
            }
            for number, interface in sorted(machine.interfaces.items(), key=lambda kv: kv[0])
            if interface is not None
        ]

        machines.append({
            "name": machine.name,
            "meta": _serialize_meta(machine.meta),
            "interfaces": interfaces,
        })

    links = [{"name": link.name} for link in lab.links.values()]

    return {
        "save_format_version": SAVE_FORMAT_VERSION,
        "lab": {
            "name": lab.name,
            "hash": lab.hash,
            "description": lab.description,
            "version": lab.version,
            "author": lab.author,
            "email": lab.email,
            "web": lab.web,
            "general_options": lab.general_options,
            "global_machine_metadata": lab.global_machine_metadata,
        },
        "machines": machines,
        "links": links,
    }


def lab_from_dict(data: Dict[str, Any]) -> Lab:
    """Rebuild a network scenario from a save manifest previously produced by `lab_to_dict`.

    Args:
        data (Dict[str, Any]): The manifest dictionary.

    Returns:
        Kathara.model.Lab.Lab: The reconstructed network scenario.
    """
    lab_info = data["lab"]

    # A saved scenario may have no name (e.g. saved from a directory without LAB_NAME). Constructing
    # `Lab(None)` would fail to compute a hash, so build with a placeholder and restore the real name.
    lab = Lab(lab_info.get("name") or "reconstructed_lab")
    lab._name = lab_info.get("name")
    # Preserve the original identity: the hash is not always derivable from the name (e.g. when the
    # scenario was reconstructed from a hash only), so restore it explicitly.
    if lab_info.get("hash"):
        lab.hash = lab_info["hash"]

    lab.description = lab_info.get("description")
    lab.version = lab_info.get("version")
    lab.author = lab_info.get("author")
    lab.email = lab_info.get("email")
    lab.web = lab_info.get("web")
    lab.general_options = lab_info.get("general_options", {}) or {}
    lab.global_machine_metadata = lab_info.get("global_machine_metadata", {}) or {}

    # Create collision domains first, so that links with no attached device are preserved as well.
    for link_info in data.get("links", []):
        lab.get_or_new_link(link_info["name"])

    for machine_info in data.get("machines", []):
        machine = lab.get_or_new_machine(machine_info["name"])
        machine.meta = _deserialize_meta(machine_info.get("meta", {}))

        for interface_info in sorted(machine_info.get("interfaces", []), key=lambda i: i["number"]):
            link = lab.get_or_new_link(interface_info["link"])
            machine.add_interface(
                link,
                number=interface_info["number"],
                mac_address=interface_info.get("mac_address"),
            )

    return lab


def _serialize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a `Machine.meta` dict into a JSON-safe form.

    The only non-JSON-safe structure is `ports`, whose keys are `(host_port, protocol)` tuples;
    it is emitted as a list of objects. Non-restorable meta keys are dropped.
    """
    result = {}
    for key, value in meta.items():
        if key in _NON_RESTORABLE_META:
            continue

        if key == "ports":
            result["ports"] = [
                {"host_port": host_port, "protocol": protocol, "guest_port": guest_port}
                for (host_port, protocol), guest_port in value.items()
            ]
        else:
            result[key] = value

    return result


def _deserialize_meta(data: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild a `Machine.meta` dict from its JSON-safe form, mirroring `Machine.__init__` defaults."""
    meta: Dict[str, Any] = {
        "exec_commands": [],
        "sysctls": {},
        "envs": {},
        "ports": {},
        "ulimits": {},
        "volumes": {},
    }

    for key, value in data.items():
        if key == "ports":
            meta["ports"] = {
                (int(port["host_port"]), port["protocol"]): int(port["guest_port"])
                for port in value
            }
        else:
            meta[key] = value

    return meta
