import logging

import requests

from ..exceptions import HTTPConnectionError

DOCKER_HUB_KATHARA_URL = "https://hub.docker.com/v2/repositories/kathara/?page_size=-1"

EXCLUDED_IMAGES = ['megalos-bgp-manager']


class DockerHubApi(object):
    @staticmethod
    def get_images() -> filter:
        """
        Get the Kathara Docker Hub account image list, excluding:
            - Private Images
            - Plugins or other types of images
            - Images in the EXCLUDED_IMAGES list

        Returns:
            filter: filtered list of currently available images that satisfy the previous conditions.

        Raises:
            HTTPConnectionError: If there is a connection error with the Docker Hub.
        """
        try:
            result = requests.get(DOCKER_HUB_KATHARA_URL)
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("Docker Hub replied with status code %s.", result.status_code)
            raise HTTPConnectionError("Docker Hub replied with status code %s." % result.status_code)

        return filter(
            lambda x: not x['is_private'] and x['repository_type'] == 'image' and x['name'] not in EXCLUDED_IMAGES,
            result.json()['results']
        )
