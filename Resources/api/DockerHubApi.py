import logging

import requests

from ..exceptions import HTTPConnectionError

DOCKER_HUB_IMAGE_URL = "https://hub.docker.com/v2/repositories/%s/tags/latest/"


class DockerHubApi(object):
    @staticmethod
    def get_image_information(image_name):
        try:
            result = requests.get(DOCKER_HUB_IMAGE_URL % image_name)
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("DockerHub replied with status code %s while looking for image %s",
                          result.status_code,
                          image_name
                          )

            raise Exception()

        return result.json()
