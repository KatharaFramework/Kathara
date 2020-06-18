import logging

import requests

from ..exceptions import HTTPConnectionError

DOCKER_HUB_IMAGE_URL = "https://hub.docker.com/v2/repositories/%s/tags/%s/"
DOCKER_HUB_KATHARA_URL = "https://hub.docker.com/v2/repositories/kathara/?page_size=-1"

EXCLUDED_IMAGES = ['megalos-bgp-manager', 'katharanp']


class DockerHubApi(object):
    @staticmethod
    def get_image_information(image_name):
        tag = 'latest'
        img_name = image_name
        if ':' in image_name:
            split_name = image_name.split(':')
            img_name, tag = split_name[0], split_name[1]
        if '/' not in img_name:
            img_name = 'library/%s' % img_name

        try:
            result = requests.get(DOCKER_HUB_IMAGE_URL % (img_name, tag))
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("DockerHub replied with status code %s while looking for image %s.",
                          result.status_code,
                          image_name
                          )
            raise HTTPConnectionError("DockerHub replied with status code %s." % result.status_code)

        return result.json()

    @staticmethod
    def get_images():
        try:
            result = requests.get(DOCKER_HUB_KATHARA_URL)
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if result.status_code != 200:
            logging.debug("DockerHub replied with status code %s.", result.status_code)
            raise HTTPConnectionError("DockerHub replied with status code %s." % result.status_code)

        return filter(lambda x: not x['is_private'] and x['name'] not in EXCLUDED_IMAGES, result.json()['results'])
