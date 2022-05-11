import logging
from typing import Dict, Any

import requests

from ..exceptions import HTTPConnectionError

GITHUB_RELEASES_URL = "https://api.github.com/repos/%s/releases/latest"
REPOSITORY_NAME = "KatharaFramework/Kathara"


class GitHubApi(object):
    @staticmethod
    def get_release_information() -> Dict[str, Any]:
        try:
            result = requests.get(GITHUB_RELEASES_URL % REPOSITORY_NAME)
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("GitHub replied with status code %s while looking for Kathara repo.", result.status_code)
            raise HTTPConnectionError("GitHub replied with status code %s." % result.status_code)

        return result.json()
