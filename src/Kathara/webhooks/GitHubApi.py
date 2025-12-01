import logging
from typing import Dict, Any

import requests

from ..exceptions import HTTPConnectionError

GITHUB_RELEASES_URL: str = "https://api.github.com/repos/%s/releases/latest"
REPOSITORY_NAME: str = "KatharaFramework/Kathara"
REQUEST_TIMEOUT: int = 1


class GitHubApi(object):
    @staticmethod
    def get_release_information() -> Dict[str, Any]:
        try:
            result = requests.get(GITHUB_RELEASES_URL % REPOSITORY_NAME, timeout=(REQUEST_TIMEOUT, REQUEST_TIMEOUT))
        except requests.exceptions.Timeout as e:
            raise HTTPConnectionError(str(e))
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("GitHub replied with status code %s while looking for Kathara repo.", result.status_code)
            raise HTTPConnectionError("GitHub replied with status code %s." % result.status_code)

        return result.json()
