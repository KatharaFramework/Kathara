import logging

import requests

from ..exceptions import HTTPConnectionError

DOCKER_HUB_KATHARA_URL = "https://hub.docker.com/v2/repositories/kathara/?page_size=-1"

EXCLUDED_IMAGES = ['megalos-bgp-manager', 'katharanp']


class DockerHubApi(object):
    @staticmethod
    def get_images() -> filter:
        try:
            result = requests.get(DOCKER_HUB_KATHARA_URL)
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("DockerHub replied with status code %s.", result.status_code)
            raise HTTPConnectionError("DockerHub replied with status code %s." % result.status_code)

        return filter(lambda x: not x['is_private'] and x['name'] not in EXCLUDED_IMAGES, result.json()['results'])
