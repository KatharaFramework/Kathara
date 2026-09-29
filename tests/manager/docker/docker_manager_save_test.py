import io
import json
import os
import sys
import tarfile
from unittest import mock
from unittest.mock import Mock

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.docker.DockerManager import DockerManager
from src.Kathara.model.Lab import Lab
from src.Kathara.exceptions import InvocationError, MachineNotFoundError


@pytest.fixture()
@mock.patch("src.Kathara.manager.docker.DockerPlugin.DockerPlugin.check_and_download_plugin")
@mock.patch("docker.client.DockerClient")
@mock.patch("docker.from_env")
def docker_manager(mock_from_env, client_mock, mock_check_and_download_plugin):
    mock_check_and_download_plugin.return_value = True
    mock_from_env.return_value = client_mock
    return DockerManager()


@pytest.fixture()
def running_lab():
    lab = Lab("Default scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/test1'})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/test2'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc2.name, "A")
    for machine in lab.machines.values():
        machine.api_object = Mock()
        machine.api_object.reload = Mock()
    return lab


def _fake_get_archive(path, content=b"data"):
    """Emulate container.get_archive: return (tar bytes iterator, stat)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(os.path.basename(path))
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return [buf.getvalue()], {"name": os.path.basename(path), "size": len(content), "mode": 0o644}


def _configure_diff(lab):
    for machine in lab.machines.values():
        machine.api_object.diff.return_value = [
            {"Path": "/root", "Kind": 0},            # directory, not a leaf -> skipped
            {"Path": "/root/NEWFILE", "Kind": 1},    # added file -> captured
            {"Path": "/etc/hosts", "Kind": 0},       # excluded (Docker-managed)
            {"Path": "/oldfile", "Kind": 2},         # deletion
        ]
        machine.api_object.get_archive.side_effect = lambda path: _fake_get_archive(path)


#
# save_lab: validation
#
def test_save_lab_invocation_error_no_target(docker_manager):
    with pytest.raises(InvocationError):
        docker_manager.save_lab("out.tar")


def test_save_lab_invocation_error_selected_and_excluded(docker_manager, running_lab):
    with pytest.raises(InvocationError):
        docker_manager.save_lab("out.tar", lab=running_lab,
                                selected_machines={"pc1"}, excluded_machines={"pc2"})


def test_save_lab_no_devices_raises(docker_manager, running_lab, tmp_path):
    docker_manager.update_lab_from_api = Mock()
    with pytest.raises(MachineNotFoundError):
        docker_manager.save_lab(str(tmp_path / "s.tar"), lab=running_lab,
                                excluded_machines={"pc1", "pc2"})


#
# save_lab: full-image mode (filesystem_diff=False)
#
def test_save_lab_full_writes_archive(docker_manager, running_lab, tmp_path):
    docker_manager.update_lab_from_api = Mock()
    docker_manager.docker_image = Mock()
    docker_manager.docker_image.commit_container.side_effect = \
        lambda container, repository, tag: f"{repository}:{tag}"
    docker_manager.docker_image.save_image_to_tar.return_value = [b"FAKE_IMG"]

    archive = str(tmp_path / "scenario.tar")
    docker_manager.save_lab(archive, lab=running_lab, filesystem_diff=False)

    assert docker_manager.docker_image.commit_container.call_count == 2
    assert docker_manager.docker_image.remove_image.call_count == 2

    with tarfile.open(archive, "r") as tar:
        names = tar.getnames()
        assert "manifest.json" in names
        assert "images/pc1.tar" in names
        assert "images/pc2.tar" in names
        manifest = json.loads(tar.extractfile("manifest.json").read().decode())
        assert manifest["save_mode"] == "full"
        pc1 = next(m for m in manifest["machines"] if m["name"] == "pc1")
        assert pc1["meta"]["image"].startswith("kathara_save_")
        assert pc1["original_image"] == "kathara/test1"


def test_save_lab_full_selected_machines(docker_manager, running_lab, tmp_path):
    docker_manager.update_lab_from_api = Mock()
    docker_manager.docker_image = Mock()
    docker_manager.docker_image.commit_container.side_effect = \
        lambda container, repository, tag: f"{repository}:{tag}"
    docker_manager.docker_image.save_image_to_tar.return_value = [b"FAKE_IMG"]

    archive = str(tmp_path / "scenario.tar")
    docker_manager.save_lab(archive, lab=running_lab, selected_machines={"pc1"}, filesystem_diff=False)

    with tarfile.open(archive, "r") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read().decode())
        assert {m["name"] for m in manifest["machines"]} == {"pc1"}
        assert "images/pc1.tar" in tar.getnames()
        assert "images/pc2.tar" not in tar.getnames()


#
# save_lab: filesystem-diff mode (default)
#
def test_save_lab_diff_writes_archive(docker_manager, running_lab, tmp_path):
    docker_manager.update_lab_from_api = Mock()
    _configure_diff(running_lab)

    archive = str(tmp_path / "scenario.tar")
    docker_manager.save_lab(archive, lab=running_lab)  # diff is the default

    with tarfile.open(archive, "r") as tar:
        names = tar.getnames()
        assert "images/pc1.diff.tar" in names
        assert "images/pc2.diff.tar" in names
        assert "images/pc1.tar" not in names  # no full images in diff mode

        manifest = json.loads(tar.extractfile("manifest.json").read().decode())
        assert manifest["save_mode"] == "diff"
        pc1 = next(m for m in manifest["machines"] if m["name"] == "pc1")
        assert pc1["original_image"] == "kathara/test1"
        assert pc1["deletions"] == ["/oldfile"]

        diff_bytes = tar.extractfile("images/pc1.diff.tar").read()

    with tarfile.open(fileobj=io.BytesIO(diff_bytes)) as diff_tar:
        diff_names = diff_tar.getnames()
        assert "root/NEWFILE" in diff_names          # added file captured with full path
        assert "etc/hosts" not in diff_names          # excluded path not captured


def test_build_device_diff_excludes_and_deletes(docker_manager):
    container = Mock()
    container.diff.return_value = [
        {"Path": "/root/keep", "Kind": 1},
        {"Path": "/run/mount", "Kind": 1},      # excluded prefix
        {"Path": "/hosthome", "Kind": 1},       # excluded exact
        {"Path": "/gone", "Kind": 2},           # deletion
        {"Path": "/dev/null", "Kind": 0},       # excluded prefix
    ]
    container.get_archive.side_effect = lambda path: _fake_get_archive(path)

    diff_path, deletions = docker_manager._build_device_diff(container)
    try:
        assert deletions == ["/gone"]
        with tarfile.open(diff_path) as tar:
            names = tar.getnames()
        assert "root/keep" in names
        assert not any(n.startswith("run") or n.startswith("hosthome") or n.startswith("dev") for n in names)
    finally:
        os.remove(diff_path)


#
# restore_lab: full-image mode
#
def _make_full_archive(path, manifest, images, lab_files=None):
    with tarfile.open(path, "w") as tar:
        def add(name, data):
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))

        add("manifest.json", json.dumps(manifest).encode())
        for name, data in images.items():
            add(f"images/{name}.tar", data)
        for name, data in (lab_files or {}).items():
            add(f"lab{name}", data)


def test_restore_lab_full_loads_images_and_deploys(docker_manager, tmp_path):
    manifest = {
        "save_format_version": 1, "save_mode": "full",
        "lab": {"name": "restored", "hash": "somehash", "general_options": {},
                "global_machine_metadata": {}},
        "machines": [{"name": "pc1", "meta": {"image": "kathara_save_x:pc1"},
                      "interfaces": [{"number": 0, "link": "A", "mac_address": None}]}],
        "links": [{"name": "A"}],
    }
    archive = str(tmp_path / "scenario.tar")
    _make_full_archive(archive, manifest, {"pc1": b"FAKE_IMG"}, {"/pc1.startup": b"echo hi\n"})

    docker_manager.docker_image = Mock()
    docker_manager.deploy_lab = Mock()

    lab = docker_manager.restore_lab(archive)

    docker_manager.docker_image.load_images_from_tar.assert_called_once()
    docker_manager.deploy_lab.assert_called_once()
    deployed = docker_manager.deploy_lab.call_args[0][0]
    assert isinstance(deployed, Lab)
    assert deployed.hash == "somehash"
    assert deployed.get_machine("pc1").meta["image"] == "kathara_save_x:pc1"
    assert lab.fs.readbytes("/pc1.startup") == b"echo hi\n"


def test_restore_lab_invalid_archive(docker_manager, tmp_path):
    archive = str(tmp_path / "bad.tar")
    with tarfile.open(archive, "w") as tar:
        data = b"nope"
        ti = tarfile.TarInfo(name="something.txt")
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))

    with pytest.raises(InvocationError):
        docker_manager.restore_lab(archive)


#
# restore_lab: filesystem-diff mode
#
def _make_diff_archive(path, manifest, diffs):
    with tarfile.open(path, "w") as tar:
        def add(name, data):
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))

        add("manifest.json", json.dumps(manifest).encode())
        for name, data in diffs.items():
            add(f"images/{name}.diff.tar", data)


def test_restore_lab_diff_builds_images_and_deploys(docker_manager, tmp_path):
    manifest = {
        "save_format_version": 1, "save_mode": "diff",
        "lab": {"name": "restored", "hash": "somehash", "general_options": {},
                "global_machine_metadata": {}},
        "machines": [{"name": "pc1", "meta": {"image": "kathara_save_h:pc1"},
                      "original_image": "kathara/test1", "deletions": ["/x"],
                      "interfaces": [{"number": 0, "link": "A", "mac_address": None}]}],
        "links": [{"name": "A"}],
    }
    archive = str(tmp_path / "scenario.tar")
    _make_diff_archive(archive, manifest, {"pc1": b"DIFFTAR"})

    docker_manager.docker_image = Mock()
    docker_manager.deploy_lab = Mock()

    lab = docker_manager.restore_lab(archive)

    docker_manager.docker_image.check_from_list.assert_called_once_with({"kathara/test1"})
    docker_manager.docker_image.build_image_from_diff.assert_called_once()
    call_args = docker_manager.docker_image.build_image_from_diff.call_args[0]
    assert call_args[0] == "kathara/test1"          # base image
    assert call_args[1] == "kathara_save_h:pc1"     # target ref
    assert call_args[3] == ["/x"]                   # deletions

    docker_manager.deploy_lab.assert_called_once()
    deployed = docker_manager.deploy_lab.call_args[0][0]
    assert deployed.get_machine("pc1").meta["image"] == "kathara_save_h:pc1"


#
# restore_lab: caller-provided network scenario (lab=)
#
def _diff_manifest_pc1():
    return {
        "save_format_version": 1, "save_mode": "diff",
        "lab": {"name": "restored", "hash": "somehash", "general_options": {},
                "global_machine_metadata": {}},
        "machines": [{"name": "pc1", "meta": {"image": "kathara_save_h:pc1"},
                      "original_image": "kathara/base", "deletions": [],
                      "interfaces": [{"number": 0, "link": "A", "mac_address": None}]}],
        "links": [{"name": "A"}],
    }


def _caller_lab():
    lab = Lab("caller scenario")
    pc1 = lab.get_or_new_machine("pc1", **{'image': 'kathara/base', 'envs': ['FOO=bar']})
    pc2 = lab.get_or_new_machine("pc2", **{'image': 'kathara/other'})
    lab.connect_machine_to_link(pc1.name, "A")
    lab.connect_machine_to_link(pc2.name, "A")
    lab.shared_path = "/tmp/shared"
    return lab


def test_restore_lab_with_lab_uses_caller_topology_and_saved_images(docker_manager, tmp_path):
    archive = str(tmp_path / "scenario.tar")
    _make_diff_archive(archive, _diff_manifest_pc1(), {"pc1": b"DIFFTAR"})

    docker_manager.docker_image = Mock()
    docker_manager.deploy_lab = Mock()

    caller_lab = _caller_lab()
    lab = docker_manager.restore_lab(archive, lab=caller_lab)

    assert lab is caller_lab
    docker_manager.deploy_lab.assert_called_once()
    assert docker_manager.deploy_lab.call_args[0][0] is caller_lab
    docker_manager.docker_image.build_image_from_diff.assert_called_once()

    assert caller_lab.get_machine("pc1").meta["image"] == "kathara_save_h:pc1"
    assert caller_lab.get_machine("pc1").meta["envs"] == {"FOO": "bar"}
    assert caller_lab.get_machine("pc2").meta["image"] == "kathara/other"
    assert caller_lab.shared_path == "/tmp/shared"
    assert set(caller_lab.machines.keys()) == {"pc1", "pc2"}


def test_restore_lab_with_lab_ignores_lab_hash(docker_manager, tmp_path):
    archive = str(tmp_path / "scenario.tar")
    _make_diff_archive(archive, _diff_manifest_pc1(), {"pc1": b"DIFFTAR"})

    docker_manager.docker_image = Mock()
    docker_manager.deploy_lab = Mock()

    caller_lab = _caller_lab()
    original_hash = caller_lab.hash
    lab = docker_manager.restore_lab(archive, lab_hash="ignoredhash", lab=caller_lab)

    assert lab.hash == original_hash
    assert lab.hash != "somehash"


def test_restore_lab_with_lab_uploads_lab_files_into_caller_fs(docker_manager, tmp_path):
    manifest = _diff_manifest_pc1()
    manifest["save_mode"] = "full"
    archive = str(tmp_path / "scenario.tar")
    _make_full_archive(archive, manifest, {"pc1": b"FAKE_IMG"}, {"/pc1.startup": b"echo hi\n"})

    docker_manager.docker_image = Mock()
    docker_manager.deploy_lab = Mock()

    caller_lab = _caller_lab()
    lab = docker_manager.restore_lab(archive, lab=caller_lab)

    assert lab is caller_lab
    assert caller_lab.fs.readbytes("/pc1.startup") == b"echo hi\n"
    docker_manager.docker_image.load_images_from_tar.assert_called_once()
