import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from unittest import mock

import pytest

sys.path.insert(0, './')

from src.Kathara.exceptions import PodmanPluginError
from src.Kathara.manager.podman.PodmanVM import PodmanVM

MACHINE = {
    "Name": "podman-machine-default",
    "State": "running",
    "Rootful": False,
    "ConnectionInfo": {"PodmanSocket": {"Path": "/var/folders/xx/T/podman/podman-machine-default-api.sock"},
                       "PodmanPipe": None},
}


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def local_vm():
    """A PodmanVM whose `run` executes the script with the local bash, as the VM does after decoding it."""
    vm = PodmanVM("/usr/bin/podman", "test-machine", "/tmp/test.sock")
    with mock.patch.object(PodmanVM, "run", autospec=True,
                           side_effect=lambda self, script, timeout=300: subprocess.run(
                               ["bash", "-c", script], capture_output=True, text=True, timeout=timeout)):
        yield vm


needs_shell_tools = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("bash", "curl", "sha256sum", "tar")),
    reason="needs bash, curl, sha256sum and tar"
)


#
# TEST: default
#
@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run")
@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value="/opt/podman/bin/podman")
def test_default_running_rootless_machine(mock_which, mock_run):
    mock_run.return_value = completed(stdout=json.dumps([MACHINE]))
    vm = PodmanVM.default()
    assert vm.name == "podman-machine-default"
    assert vm.podman == "/opt/podman/bin/podman"
    assert vm.socket_url == "unix:///var/folders/xx/T/podman/podman-machine-default-api.sock"
    assert mock_run.call_args.args[0] == ["/opt/podman/bin/podman", "machine", "inspect"]


@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value=None)
def test_default_podman_not_installed(mock_which):
    with pytest.raises(PodmanPluginError, match="https://podman.io"):
        PodmanVM.default()


@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run")
@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value="/opt/podman/bin/podman")
def test_default_no_machine(mock_which, mock_run):
    mock_run.return_value = completed(stderr="Error: podman-machine-default: VM does not exist", returncode=125)
    with pytest.raises(PodmanPluginError, match="podman machine init"):
        PodmanVM.default()


@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run")
@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value="/opt/podman/bin/podman")
def test_default_machine_stopped(mock_which, mock_run):
    mock_run.return_value = completed(stdout=json.dumps([dict(MACHINE, State="stopped")]))
    with pytest.raises(PodmanPluginError, match="podman machine start"):
        PodmanVM.default()


@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run")
@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value="/opt/podman/bin/podman")
def test_default_machine_rootful(mock_which, mock_run):
    mock_run.return_value = completed(stdout=json.dumps([dict(MACHINE, Rootful=True)]))
    with pytest.raises(PodmanPluginError, match="--rootful=false"):
        PodmanVM.default()


@pytest.mark.parametrize("stdout", ["not json", "[]", json.dumps([{"Name": "m"}]), json.dumps({"Name": "m"})])
@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run")
@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value="/opt/podman/bin/podman")
def test_default_unexpected_inspect_output(mock_which, mock_run, stdout):
    mock_run.return_value = completed(stdout=stdout)
    with pytest.raises(PodmanPluginError, match="Cannot read the output"):
        PodmanVM.default()


@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="podman", timeout=30))
@mock.patch("src.Kathara.manager.podman.PodmanVM.shutil.which", return_value="/opt/podman/bin/podman")
def test_default_inspect_timeout(mock_which, mock_run):
    with pytest.raises(PodmanPluginError, match="did not answer"):
        PodmanVM.default()


#
# TEST: normalize_arch
#
@pytest.mark.parametrize("raw,expected", [("x86_64", "amd64"), ("aarch64\n", "arm64"), ("ARM64", "arm64"),
                                          ("riscv64", "riscv64")])
def test_normalize_arch(raw, expected):
    assert PodmanVM.normalize_arch(raw) == expected


#
# TEST: run / run_checked
#
@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run")
def test_run_sends_the_script_base64_encoded(mock_run):
    mock_run.return_value = completed(stdout="ok")
    vm = PodmanVM("/opt/podman/bin/podman", "my-machine", "/tmp/s.sock")
    script = "echo \"$HOME\" 'quoted' `id`"
    assert vm.run(script, timeout=12).stdout == "ok"

    args = mock_run.call_args.args[0]
    assert args[:4] == ["/opt/podman/bin/podman", "machine", "ssh", "my-machine"]
    encoded = args[4].split()[1]
    assert args[4] == f"echo {encoded} | base64 -d | bash"
    assert base64.b64decode(encoded).decode() == script
    assert mock_run.call_args.kwargs["timeout"] == 12


@mock.patch("src.Kathara.manager.podman.PodmanVM.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="podman", timeout=5))
def test_run_timeout(mock_run):
    with pytest.raises(PodmanPluginError, match="did not finish in 5s"):
        PodmanVM("/opt/podman/bin/podman", "my-machine", "/tmp/s.sock").run("sleep 10", timeout=5)


@mock.patch("src.Kathara.manager.podman.PodmanVM.PodmanVM.run")
def test_run_checked_raises_on_failure(mock_run):
    mock_run.return_value = completed(stderr="boom\n", returncode=1)
    with pytest.raises(PodmanPluginError, match="Cannot do something in the podman machine `m`: boom"):
        PodmanVM("/opt/podman/bin/podman", "m", "/tmp/s.sock").run_checked("false", "do something")


@mock.patch("src.Kathara.manager.podman.PodmanVM.PodmanVM.run")
def test_run_checked_returns_the_result(mock_run):
    mock_run.return_value = completed(stdout="ok")
    assert PodmanVM("/opt/podman/bin/podman", "m", "/tmp/s.sock").run_checked("true", "x").stdout == "ok"


#
# TEST: query, write_file, install_archive (scripts executed with the local bash)
#
@pytest.fixture
def vm():
    yield from local_vm()


@needs_shell_tools
def test_query_one_line_per_command(vm, tmp_path):
    result = vm.query(["echo first", f"cat {tmp_path}/missing", "printf 'a\\nb\\n'", "false", "echo last"])
    assert result == ["first", "", "ab", "", "last"]


@needs_shell_tools
def test_write_file_is_byte_identical(vm, tmp_path):
    content = '# Managed\n[network]\nnetavark_plugin_dirs = ["/home/a b/bin", {append=true}]\n$HOME `id` \'q\' "d"\n'
    path = str(tmp_path / "dir with space" / "containers.conf.d" / "kathara.conf")
    vm.write_file(path, content)
    with open(path) as f:
        assert f.read() == content
    assert not os.path.exists(path + ".tmp")


def make_bundle(tmp_path, version):
    data = ("#!/bin/sh\necho '{\"version\": \"%s\"}'\n" % version).encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("katharanp/bin/katharanp_vde")
        info.size, info.mode = len(data), 0o755
        archive.addfile(info, io.BytesIO(data))
    bundle = tmp_path / f"bundle-{version}.tar.gz"
    bundle.write_bytes(buffer.getvalue())
    return f"file://{bundle}", hashlib.sha256(buffer.getvalue()).hexdigest()


@needs_shell_tools
def test_install_archive_replaces_the_old_installation(vm, tmp_path):
    dest = tmp_path / "data" / "kathara" / "katharanp"
    (dest / "stale").mkdir(parents=True)
    url, sha256 = make_bundle(tmp_path, "v9")

    vm.install_archive(url, sha256, str(dest), "katharanp")

    assert sorted(os.listdir(dest)) == ["bin"]
    assert sorted(os.listdir(dest.parent)) == ["katharanp"]
    assert vm.query([f'"{dest}/bin/katharanp_vde" info']) == ['{"version": "v9"}']


@needs_shell_tools
def test_install_archive_bad_checksum_keeps_the_old_installation(vm, tmp_path):
    dest = tmp_path / "katharanp"
    url, sha256 = make_bundle(tmp_path, "v1")
    vm.install_archive(url, sha256, str(dest), "katharanp")
    url2, _ = make_bundle(tmp_path, "v2")

    with pytest.raises(PodmanPluginError, match="Cannot install"):
        vm.install_archive(url2, "0" * 64, str(dest), "katharanp")

    assert vm.query([f'"{dest}/bin/katharanp_vde" info']) == ['{"version": "v1"}']


@needs_shell_tools
def test_install_archive_download_error(vm, tmp_path):
    with pytest.raises(PodmanPluginError, match="Cannot install"):
        vm.install_archive(f"file://{tmp_path}/missing.tar.gz", "0" * 64, str(tmp_path / "katharanp"), "katharanp")
    assert not (tmp_path / "katharanp").exists()


@mock.patch("src.Kathara.manager.podman.PodmanVM.PodmanVM.run_checked")
def test_restart_podman(mock_run_checked):
    PodmanVM("/opt/podman/bin/podman", "m", "/tmp/s.sock").restart_podman()
    assert mock_run_checked.call_args.args[0] == "systemctl --user try-restart podman.service"