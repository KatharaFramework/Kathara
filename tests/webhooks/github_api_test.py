import sys
from unittest import mock

import pytest
import requests.exceptions

sys.path.insert(0, './')

from src.Kathara.webhooks.GitHubApi import GitHubApi, GITHUB_RELEASES_URL, REPOSITORY_NAME, REQUEST_TIMEOUT
from src.Kathara.exceptions import HTTPConnectionError


@pytest.fixture()
@mock.patch("requests.Response")
def github_get_release_information_response(mock_response):
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tag_name": "9.9.9",
        "target_commitish": "main",
    }
    return mock_response


@mock.patch("requests.get")
def test_get_release_information(mock_requests_get, github_get_release_information_response):
    mock_requests_get.return_value = github_get_release_information_response
    release_info = GitHubApi.get_release_information()
    mock_requests_get.assert_called_once_with(
        GITHUB_RELEASES_URL % REPOSITORY_NAME, timeout=(REQUEST_TIMEOUT, REQUEST_TIMEOUT)
    )
    assert release_info["tag_name"] == "9.9.9"


@mock.patch("requests.get")
def test_get_release_information_connection_error(mock_requests_get):
    mock_requests_get.side_effect = requests.exceptions.ConnectionError
    with pytest.raises(HTTPConnectionError):
        GitHubApi.get_release_information()


@mock.patch("requests.get")
def test_get_release_information_status_code_error(mock_requests_get):
    mock_requests_get.status_code = 404
    with pytest.raises(HTTPConnectionError):
        GitHubApi.get_release_information()


@mock.patch("requests.get")
def test_get_release_information_timeout_error(mock_requests_get):
    mock_requests_get.side_effect = requests.exceptions.Timeout

    with pytest.raises(HTTPConnectionError):
        GitHubApi.get_release_information()
