import sys
from unittest import mock
from unittest.mock import Mock

import pytest
from podman.errors import APIError

sys.path.insert(0, './')

from src.Kathara.manager.podman.PodmanImage import PodmanImage


@pytest.fixture()
def podman_image():
    image = PodmanImage(Mock())
    image.libpodCompat = Mock()
    return image


def _local_image(repo_digests):
    image = Mock()
    image.attrs = {"RepoDigests": repo_digests}
    return image


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.utils.get_architecture", return_value="amd64")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_found(mock_get_local, mock_get_architecture, mock_dispatcher_cls, podman_image):
    mock_get_local.return_value = _local_image(["docker.io/kathara/test@sha256:old"])
    podman_image.libpodCompat.inspect_remote_manifest.return_value = {
        "manifests": [
            {"digest": "sha256:new", "platform": {"os": "linux", "architecture": "amd64"}}
        ]
    }

    podman_image.check_for_updates("kathara/test")

    podman_image.libpodCompat.inspect_remote_manifest.assert_called_once_with("docker.io/kathara/test")
    mock_dispatcher_cls.get_instance.return_value.dispatch.assert_called_once_with(
        "docker_image_update_found", docker_image=podman_image, image_name="kathara/test"
    )


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.utils.get_architecture", return_value="amd64")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_up_to_date_matches_second_digest(mock_get_local, mock_get_architecture,
                                                              mock_dispatcher_cls, podman_image):
    mock_get_local.return_value = _local_image([
        "docker.io/kathara/test@sha256:index",
        "docker.io/kathara/test@sha256:instance"
    ])
    podman_image.libpodCompat.inspect_remote_manifest.return_value = {
        "manifests": [
            {"digest": "sha256:instance", "platform": {"os": "linux", "architecture": "amd64"}}
        ]
    }

    podman_image.check_for_updates("kathara/test")

    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_digest_reference_skipped(mock_get_local, mock_dispatcher_cls, podman_image):
    podman_image.check_for_updates("kathara/test@sha256:abc")

    assert not mock_get_local.called
    assert not podman_image.libpodCompat.inspect_remote_manifest.called
    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_localhost_skipped_without_request(mock_get_local, mock_dispatcher_cls, podman_image):
    podman_image.check_for_updates("localhost/test")

    assert not mock_get_local.called
    assert not podman_image.libpodCompat.inspect_remote_manifest.called
    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_empty_repo_digests_skipped(mock_get_local, mock_dispatcher_cls, podman_image):
    mock_get_local.return_value = _local_image([])

    podman_image.check_for_updates("kathara/test")

    mock_get_local.assert_called_once_with("kathara/test")
    assert not podman_image.libpodCompat.inspect_remote_manifest.called
    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_registry_error_swallowed(mock_get_local, mock_dispatcher_cls, podman_image):
    mock_get_local.return_value = _local_image(["docker.io/kathara/test@sha256:old"])
    podman_image.libpodCompat.inspect_remote_manifest.side_effect = APIError(
        "pinging container registry localhost: ... connection refused"
    )

    podman_image.check_for_updates("kathara/test")

    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_no_manifests_key_skipped(mock_get_local, mock_dispatcher_cls, podman_image):
    mock_get_local.return_value = _local_image(["docker.io/kathara/test@sha256:old"])
    podman_image.libpodCompat.inspect_remote_manifest.return_value = {
        "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json"
    }

    podman_image.check_for_updates("kathara/test")

    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called


@mock.patch("src.Kathara.manager.podman.PodmanImage.EventDispatcher")
@mock.patch("src.Kathara.utils.get_architecture", return_value="amd64")
@mock.patch("src.Kathara.manager.podman.PodmanImage.PodmanImage.get_local")
def test_check_for_updates_no_matching_architecture_skipped(mock_get_local, mock_get_architecture,
                                                              mock_dispatcher_cls, podman_image):
    mock_get_local.return_value = _local_image(["docker.io/kathara/test@sha256:old"])
    podman_image.libpodCompat.inspect_remote_manifest.return_value = {
        "manifests": [
            {"digest": "sha256:arm", "platform": {"os": "linux", "architecture": "arm64"}}
        ]
    }

    podman_image.check_for_updates("kathara/test")

    assert not mock_dispatcher_cls.get_instance.return_value.dispatch.called
