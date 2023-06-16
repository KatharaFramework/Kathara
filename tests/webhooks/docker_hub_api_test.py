import sys
from unittest import mock

import pytest
import requests.exceptions

sys.path.insert(0, './')

from src.Kathara.webhooks.DockerHubApi import DockerHubApi, EXCLUDED_IMAGES, DOCKER_HUB_KATHARA_IMAGES_URL, \
    DOCKER_HUB_KATHARA_TAGS_URL
from src.Kathara.exceptions import HTTPConnectionError

EXCLUDED_IMAGES.append("excluded")


@pytest.fixture()
@mock.patch("requests.Response")
def docker_hub_get_images_response(mock_response):
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'results': [
            {'name': 'test', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'},
            {'name': 'test-2', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'},
            {'name': 'test-3', 'namespace': 'kathara', 'is_private': True, 'repository_type': 'image'},
            {'name': 'excluded', 'namespace': 'kathara', 'is_private': True, 'repository_type': 'image'}
        ]
    }
    return mock_response


@pytest.fixture()
@mock.patch("requests.Response")
def docker_hub_get_tags_response(mock_response):
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'results': [
            {'name': 'latest', 'digest': '11111', 'tag_status': 'active', 'repository_type': 'image'},
            {'name': 'tag-latest', 'digest': '11111', 'tag_status': 'active', 'repository_type': 'image'},
            {'name': 'tag-1', 'digest': '22222', 'tag_status': 'active', 'repository_type': 'image'},
            {'name': 'tag-2', 'digest': '22222', 'tag_status': 'active', 'repository_type': 'image'},
            {'name': 'tag-1', 'digest': '33333', 'tag_status': 'inactive', 'repository_type': 'image'},
        ]
    }
    return mock_response


#
# TEST: get_images()
#
@mock.patch("requests.get")
def test_get_images(mock_requests_get, docker_hub_get_images_response):
    mock_requests_get.return_value = docker_hub_get_images_response
    images = list(DockerHubApi.get_images())
    mock_requests_get.assert_called_once_with(DOCKER_HUB_KATHARA_IMAGES_URL)
    assert len(images) == 2
    assert images[0]['name'] == 'test'
    assert images[1]['name'] == 'test-2'


@mock.patch("requests.get")
def test_get_images_connection_error(mock_requests_get):
    mock_requests_get.side_effect = requests.exceptions.ConnectionError
    with pytest.raises(HTTPConnectionError):
        DockerHubApi.get_images()


@mock.patch("requests.get")
def test_get_images_status_code_error(mock_requests_get):
    mock_requests_get.status_code = 404
    with pytest.raises(HTTPConnectionError):
        DockerHubApi.get_images()


#
# TEST: get_tagged_images()
#
@mock.patch("requests.get")
@mock.patch("src.Kathara.webhooks.DockerHubApi.DockerHubApi.get_images")
def test_get_tagged_images(mock_get_images, mock_requests_get, docker_hub_get_tags_response):
    mock_get_images.return_value = [
        {'name': 'test-0', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'},
        {'name': 'test-1', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'}
    ]
    mock_requests_get.return_value = docker_hub_get_tags_response
    tagged_images = DockerHubApi.get_tagged_images()

    calls = [
        mock.call(DOCKER_HUB_KATHARA_TAGS_URL.format(image_name="kathara/test-0")),
        mock.call(DOCKER_HUB_KATHARA_TAGS_URL.format(image_name="kathara/test-1"))
    ]
    mock_requests_get.assert_has_calls(calls, any_order=True)
    assert len(tagged_images) == 8
    assert 'kathara/test-0' in tagged_images
    assert 'kathara/test-0:tag-latest' in tagged_images
    assert 'kathara/test-0:tag-1' in tagged_images
    assert 'kathara/test-0:tag-2' in tagged_images
    assert 'kathara/test-1' in tagged_images
    assert 'kathara/test-1:tag-latest' in tagged_images
    assert 'kathara/test-1:tag-1' in tagged_images
    assert 'kathara/test-1:tag-2' in tagged_images


@mock.patch("requests.get")
@mock.patch("src.Kathara.webhooks.DockerHubApi.DockerHubApi.get_images")
def test_get_tagged_images_connection_error(mock_get_images, mock_requests_get):
    mock_get_images.return_value = [
        {'name': 'test-0', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'},
        {'name': 'test-1', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'}
    ]
    mock_requests_get.side_effect = requests.exceptions.ConnectionError
    with pytest.raises(HTTPConnectionError):
        DockerHubApi.get_tagged_images()


@mock.patch("requests.get")
@mock.patch("src.Kathara.webhooks.DockerHubApi.DockerHubApi.get_images")
def test_get_tagged_images_status_code_error(mock_get_images, mock_requests_get):
    mock_get_images.return_value = [
        {'name': 'test-0', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'},
        {'name': 'test-1', 'namespace': 'kathara', 'is_private': False, 'repository_type': 'image'}
    ]
    mock_requests_get.status_code = 404
    with pytest.raises(HTTPConnectionError):
        DockerHubApi.get_tagged_images()
