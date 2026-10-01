import json
import struct
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from podman.domain.containers import Container
from podman.domain.networks import Network
from podman.errors import APIError

from src.Kathara.manager.podman.libpod_compat import LibpodCompat


def _frame(stream: int, data: bytes) -> bytes:
    """Build a multiplexed frame: 1 byte stream type, 3 zero bytes, 4 bytes big-endian size."""
    return struct.pack(">BxxxI", stream, len(data)) + data


def _libpod_mock(json_body=None, content=b"", status_code=200):
    api = Mock()
    resp = Mock()
    resp.json.return_value = json_body or {}
    resp.content = content
    resp.status_code = status_code
    api.post.return_value = resp
    api.get.return_value = resp
    return LibpodCompat(Mock(api=api)), api, resp


# exec_create

def test_exec_create_builds_expected_payload():
    libpod, api, resp = _libpod_mock(json_body={"Id": "exec123"})

    exec_id = libpod.exec_create("container1", ["ls", "-la"], tty=True, privileged=True, user="root")

    assert exec_id == "exec123"
    args, kwargs = api.post.call_args
    assert args[0] == "/containers/container1/exec"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    payload = json.loads(kwargs["data"])
    assert payload["Cmd"] == ["ls", "-la"]
    assert payload["Tty"] is True
    assert payload["Privileged"] is True
    assert payload["User"] == "root"
    resp.raise_for_status.assert_called_once()


def test_exec_create_splits_string_command():
    libpod, api, _ = _libpod_mock(json_body={"Id": "exec123"})

    libpod.exec_create("container1", "ls")
    assert json.loads(api.post.call_args.kwargs["data"])["Cmd"] == ["ls"]

    libpod.exec_create("container1", "cat /tmp/EOS")
    assert json.loads(api.post.call_args.kwargs["data"])["Cmd"] == ["cat", "/tmp/EOS"]


def test_exec_create_omits_empty_user():
    libpod, api, _ = _libpod_mock(json_body={"Id": "exec123"})

    libpod.exec_create("container1", "ls")

    assert "User" not in json.loads(api.post.call_args.kwargs["data"])


def test_exec_create_converts_environment_dict():
    libpod, api, _ = _libpod_mock(json_body={"Id": "exec123"})

    libpod.exec_create("container1", "ls", environment={"A": "1", "B": "2"})

    payload = json.loads(api.post.call_args.kwargs["data"])
    assert set(payload["Env"]) == {"A=1", "B=2"}


# exec_start

def test_exec_start_buffered_strips_multiplexing_headers():
    content = _frame(1, b"out\n") + _frame(2, b"err\n")
    libpod, _, resp = _libpod_mock(content=content)

    output = libpod.exec_start("exec123", tty=False, demux=False, stream=False)

    assert output == b"out\nerr\n"
    resp.raise_for_status.assert_called_once()


def test_exec_start_tty_returns_raw_content():
    libpod, _, _ = _libpod_mock(content=b"hello")

    assert libpod.exec_start("exec123", tty=True) == b"hello"


def test_exec_start_demux_separates_streams():
    content = _frame(1, b"out\n") + _frame(2, b"err\n")
    libpod, _, _ = _libpod_mock(content=content)

    stdout, stderr = libpod.exec_start("exec123", demux=True)

    assert stdout == b"out\n"
    assert stderr == b"err\n"


def test_exec_start_detach_disables_stream():
    libpod, api, _ = _libpod_mock(content=b"")

    libpod.exec_start("exec123", detach=True, stream=True)

    assert api.post.call_args.kwargs["stream"] is False
    assert json.loads(api.post.call_args.kwargs["data"])["Detach"] is True


# exec_start_hijack

def test_exec_start_hijack_returns_blocking_socket():
    libpod, api, resp = _libpod_mock(status_code=101)
    sock = resp.raw.connection.sock

    result = libpod.exec_start_hijack("exec123", tty=True)

    assert result is sock
    assert sock._hijacked_response is resp
    sock.settimeout.assert_called_once_with(None)
    headers = api.post.call_args.kwargs["headers"]
    assert headers["Connection"] == "Upgrade"
    assert headers["Upgrade"] == "tcp"


def test_exec_start_hijack_raises_on_error_status():
    libpod, _, resp = _libpod_mock(status_code=409)
    resp.raise_for_status.side_effect = APIError("cannot exec in a container that is not running")

    with pytest.raises(APIError):
        libpod.exec_start_hijack("exec123")

    resp.raw.connection.sock.settimeout.assert_not_called()


def test_exec_start_hijack_raises_on_unexpected_success_status():
    libpod, _, _ = _libpod_mock(status_code=200)

    with pytest.raises(APIError) as exc:
        libpod.exec_start_hijack("exec123")

    # str(APIError) formats the (mocked) response: check the message argument instead
    assert "101" in exc.value.args[0]


# exec_inspect / exec_resize

def test_exec_inspect_returns_exit_code():
    libpod, api, _ = _libpod_mock(json_body={"ExitCode": 0, "Running": False})

    result = libpod.exec_inspect("exec123")

    assert result["ExitCode"] == 0
    api.get.assert_called_once_with("/exec/exec123/json")


def test_exec_resize_uses_h_w_params():
    libpod, api, resp = _libpod_mock()

    libpod.exec_resize("exec123", cols=80, rows=24)

    api.post.assert_called_once_with("/exec/exec123/resize", params={"h": 24, "w": 80})
    resp.raise_for_status.assert_called_once()


# sysctl_options

def test_sysctl_options_empty():
    assert LibpodCompat.sysctl_options(None) == {}
    assert LibpodCompat.sysctl_options({}) == {}


def test_sysctl_options_adds_prefix_and_stringifies():
    options = LibpodCompat.sysctl_options({"net.ipv4.conf.eth1.rp_filter": 0,
                                           "net.ipv4.conf.eth1.arp_ignore": "2"})

    assert options == {"sysctl.net.ipv4.conf.eth1.rp_filter": "0",
                       "sysctl.net.ipv4.conf.eth1.arp_ignore": "2"}


# network_connect

def test_network_connect_minimal_body():
    libpod, api, resp = _libpod_mock()

    libpod.network_connect("net_a", "container1", "eth1")

    args, kwargs = api.post.call_args
    assert args[0] == "/networks/net_a/connect"
    assert json.loads(kwargs["data"]) == {"container": "container1", "interface_name": "eth1"}
    resp.raise_for_status.assert_called_once()


def test_network_connect_full_body():
    libpod, api, _ = _libpod_mock()

    libpod.network_connect("net_a", "container1", "eth1", mac_address="02:00:00:00:00:01",
                           sysctls={"net.ipv4.conf.eth1.rp_filter": 0}, aliases=["kathara-eth1"])

    assert json.loads(api.post.call_args.kwargs["data"]) == {
        "container": "container1",
        "interface_name": "eth1",
        "static_mac": "02:00:00:00:00:01",
        "options": {"sysctl.net.ipv4.conf.eth1.rp_filter": "0"},
        "aliases": ["kathara-eth1"],
    }


def test_network_connect_aliases_omitted_when_not_set():
    libpod, api, _ = _libpod_mock()

    libpod.network_connect("net_a", "container1", "eth1")

    assert "aliases" not in json.loads(api.post.call_args.kwargs["data"])


def test_network_connect_aliases_omitted_when_empty():
    libpod, api, _ = _libpod_mock()

    libpod.network_connect("net_a", "container1", "eth1", aliases=[])

    assert "aliases" not in json.loads(api.post.call_args.kwargs["data"])


def test_network_connect_accepts_podman_objects():
    libpod, api, _ = _libpod_mock()
    network = Mock(spec=Network)
    network.name = "net_a"
    container = Mock(spec=Container)
    container.id = "abc123"

    libpod.network_connect(network, container, "eth1")

    args, kwargs = api.post.call_args
    assert args[0] == "/networks/net_a/connect"
    assert json.loads(kwargs["data"])["container"] == "abc123"


def test_network_connect_propagates_plugin_error():
    libpod, _, resp = _libpod_mock()
    resp.raise_for_status.side_effect = APIError('plugin "katharanp" failed: sysctl ... non_esiste')

    with pytest.raises(APIError, match="katharanp"):
        libpod.network_connect("net_a", "container1", "eth1", sysctls={"net.ipv4.conf.eth1.non_esiste": 1})


# inspect_remote_manifest

def test_inspect_remote_manifest_builds_expected_request():
    libpod, api, resp = _libpod_mock(json_body={"schemaVersion": 2, "manifests": []})

    result = libpod.inspect_remote_manifest("docker.io/kathara/base:latest")

    assert result == {"schemaVersion": 2, "manifests": []}
    args, kwargs = api.get.call_args
    assert args[0] == "/manifests/docker.io/kathara/base:latest/json"
    assert kwargs["params"] == {"tlsVerify": "true"}
    resp.raise_for_status.assert_called_once()


def test_inspect_remote_manifest_encodes_name():
    libpod, api, _ = _libpod_mock(json_body={})

    libpod.inspect_remote_manifest("docker.io/kathara/base@sha256:abc")

    args, _ = api.get.call_args
    assert args[0] == "/manifests/docker.io/kathara/base%40sha256:abc/json"


def test_inspect_remote_manifest_raises_on_error():
    libpod, _, resp = _libpod_mock(status_code=404, json_body={"cause": "not found", "message": "not found"})
    resp.raise_for_status.side_effect = APIError("not found")

    with pytest.raises(APIError):
        libpod.inspect_remote_manifest("docker.io/kathara/missing:latest")