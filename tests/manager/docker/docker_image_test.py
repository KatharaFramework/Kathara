import sys
from unittest import mock

import docker.models.images
import pytest
from docker.errors import APIError

sys.path.insert(0, './')

from src.Kathara.exceptions import InvalidImageArchitectureError
from src.Kathara.event.EventDispatcher import EventDispatcher
from src.Kathara.manager.docker.DockerImage import DockerImage


class MockPullEvent(object):
    def run(self, docker_image, image_name):
        docker_image.pull(image_name)


EventDispatcher.get_instance().register("docker_image_update_found", MockPullEvent())


@pytest.fixture()
@mock.patch("docker.DockerClient")
def docker_image(mock_client):
    return DockerImage(mock_client)


def test_get_local(docker_image):
    docker_image.get_local("kathara/test")
    docker_image.client.images.get.assert_called_once_with("kathara/test")


def test_get_remote(docker_image):
    docker_image.get_remote("kathara/test")
    docker_image.client.images.get_registry_data.assert_called_once_with("kathara/test")


def test_pull(docker_image):
    docker_image.pull("kathara/test")
    docker_image.client.images.pull.assert_called_once_with("kathara/test:latest")


def test_pull_latest(docker_image):
    docker_image.pull("kathara/test:latest")
    docker_image.client.images.pull.assert_called_once_with("kathara/test:latest")


def test_pull_tag(docker_image):
    docker_image.pull("kathara/test:tag")
    docker_image.client.images.pull.assert_called_once_with("kathara/test:tag")


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
@mock.patch("docker.models.images.Image")
def test_check_for_updates_local_image(mock_image, mock_get_local, mock_get_remote, mock_pull, docker_image):
    mock_image.configure_mock(**{
        'attrs': {
            'RepoDigests': None
        }
    })
    mock_get_local.return_value = mock_image
    docker_image.check_for_updates("kathara/test")
    mock_get_local.assert_called_once_with("kathara/test")
    assert not mock_get_remote.called
    assert not mock_pull.called


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
@mock.patch("docker.models.images.Image")
@mock.patch("docker.models.images.Image")
def test_check_for_updates_remote_image(mock_local_image, mock_remote_image, mock_get_local, mock_get_remote,
                                        mock_pull, docker_image):
    mock_local_image.configure_mock(**{
        'attrs': {
            'RepoDigests': ['kathara/test@sha256']
        }
    })
    mock_remote_image.configure_mock(**{
        'attrs': {
            'Descriptor': {
                'digest': 'sha256'
            }
        }
    })
    mock_get_local.return_value = mock_local_image
    mock_get_remote.return_value = mock_remote_image
    docker_image.check_for_updates("kathara/test")
    mock_get_local.assert_called_once_with("kathara/test")
    mock_get_remote.assert_called_once_with("kathara/test")
    assert not mock_pull.called


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
@mock.patch("docker.models.images.Image")
@mock.patch("docker.models.images.Image")
def test_check_for_updates_image_update(mock_local_image, mock_remote_image, mock_get_local, mock_get_remote,
                                        mock_pull, docker_image):
    mock_local_image.configure_mock(**{
        'attrs': {
            'RepoDigests': ['kathara/test@sha256']
        }
    })
    mock_remote_image.configure_mock(**{
        'attrs': {
            'Descriptor': {
                'digest': 'different_sha'
            }
        }
    })
    mock_get_local.return_value = mock_local_image
    mock_get_remote.return_value = mock_remote_image
    docker_image.check_for_updates("kathara/test")
    mock_get_local.assert_called_once_with("kathara/test")
    mock_get_remote.assert_called_once_with("kathara/test")
    mock_pull.assert_called_once_with("kathara/test")


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_image_architecture")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.check_for_updates")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
def test_check_and_pull_local_false(mock_get_local, mock_check_for_updates, mock_get_remote, mock_pull,
                                    mock_check_image_architecture, docker_image):
    mock_check_image_architecture.return_value = None

    docker_image._check_and_pull("kathara/test", False)
    mock_get_local.assert_called_once_with("kathara/test")
    assert not mock_get_remote.called
    assert not mock_check_for_updates.called
    assert not mock_pull.called


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_image_architecture")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.check_for_updates")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
def test_check_and_pull_local_true(mock_get_local, mock_check_for_updates, mock_get_remote, mock_pull,
                                   mock_check_image_architecture, docker_image):
    mock_check_image_architecture.return_value = None

    docker_image._check_and_pull("kathara/test", True)
    mock_get_local.assert_called_once_with("kathara/test")
    mock_check_for_updates.assert_called_once_with("kathara/test")
    assert not mock_get_remote.called
    assert not mock_pull.called


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_image_architecture")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.check_for_updates")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
def test_check_and_pull_remote_false(mock_get_local, mock_check_for_updates, mock_get_remote, mock_pull,
                                     mock_check_image_architecture, docker_image):
    mock_check_image_architecture.return_value = None

    mock_get_local.side_effect = APIError("Fail")
    docker_image._check_and_pull("kathara/exception", False)
    mock_get_local.assert_called_once_with("kathara/exception")
    assert not mock_check_for_updates.called
    mock_get_remote.assert_called_once_with("kathara/exception")
    assert not mock_pull.called


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_image_architecture")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.check_for_updates")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
def test_check_and_pull_remote_true(mock_get_local, mock_check_for_updates, mock_get_remote, mock_pull,
                                    mock_check_image_architecture, docker_image):
    mock_check_image_architecture.return_value = None

    mock_get_local.side_effect = APIError("Fail")
    docker_image._check_and_pull("kathara/test", True)
    mock_get_local.assert_called_once_with("kathara/test")
    assert not mock_check_for_updates.called
    mock_get_remote.assert_called_once_with("kathara/test")
    mock_pull.assert_called_once_with("kathara/test")


@mock.patch("src.Kathara.utils.get_architecture")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.check_for_updates")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
def test_check_and_pull_local_incompatible_arch(mock_get_local, mock_check_for_updates, mock_get_remote, mock_pull,
                                                mock_get_architecture, docker_image):
    image_obj = docker.models.images.Image()
    image_obj.attrs['Architecture'] = 'amd64'

    mock_get_local.return_value = image_obj
    mock_get_architecture.return_value = "arm64"

    with pytest.raises(Exception):
        docker_image._check_and_pull("kathara/test", False)

    mock_get_local.assert_called_once_with("kathara/test")
    assert not mock_check_for_updates.called
    assert not mock_get_remote.called
    assert not mock_pull.called


@mock.patch("src.Kathara.utils.get_architecture")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.pull")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_remote")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.check_for_updates")
@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage.get_local")
def test_check_and_pull_remote_incompatible_arch(mock_get_local, mock_check_for_updates, mock_get_remote, mock_pull,
                                                 mock_get_architecture, docker_image):
    registry_data = docker.models.images.RegistryData("kathara/remote")
    registry_data.attrs['Platforms'] = [{'os': 'linux', 'architecture': 'amd64'}]

    mock_get_remote.return_value = registry_data
    mock_get_architecture.return_value = "arm64"

    mock_get_local.side_effect = APIError("Fail")

    with pytest.raises(Exception):
        docker_image._check_and_pull("kathara/remote", False)
    mock_get_local.assert_called_once_with("kathara/remote")
    assert not mock_check_for_updates.called
    mock_get_remote.assert_called_once_with("kathara/remote")
    assert not mock_pull.called


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_and_pull")
def test_check(mock_check_and_pull, docker_image):
    docker_image.check("kathara/test")
    mock_check_and_pull.assert_called_once_with("kathara/test", pull=False)


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_and_pull")
def test_check_and_pull_from_list_3_elem(mock_check_and_pull, docker_image):
    images = ["kathara/test1", "kathara/test2", "kathara/test3"]
    docker_image.check_from_list(images)
    mock_check_and_pull.assert_any_call("kathara/test1")
    mock_check_and_pull.assert_any_call("kathara/test2")
    mock_check_and_pull.assert_any_call("kathara/test3")
    assert mock_check_and_pull.call_count == 3


@mock.patch("src.Kathara.manager.docker.DockerImage.DockerImage._check_and_pull")
def test_check_and_pull_from_list_0_elem(mock_check_and_pull, docker_image):
    images = []
    docker_image.check_from_list(images)
    assert not mock_check_and_pull.called
