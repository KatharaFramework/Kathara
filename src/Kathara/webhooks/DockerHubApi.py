import logging
from functools import partial
from multiprocessing.dummy import Pool

import requests

from ..exceptions import HTTPConnectionError
from ..utils import get_pool_size, chunk_list

DOCKER_HUB_KATHARA_URL = "https://hub.docker.com/v2/repositories/kathara/?page_size=-1"

EXCLUDED_IMAGES = ['megalos-bgp-manager']


class DockerHubApi(object):
    @staticmethod
    def get_images() -> filter:
        """Retrieve the list of available Kathara images on Docker Hub.

        This method retrieves the list of images from the Kathara Docker Hub account, excluding private images,
        plugins, and images specified in the EXCLUDED_IMAGES list.

        Returns:
            filter: A filtered list of currently available images that satisfy the specified conditions.

        Raises:
            HTTPConnectionError: If there is a connection error with the Docker Hub.
        """
        try:
            logging.debug("Getting Kathara images from Docker Hub...")
            response = requests.get(DOCKER_HUB_KATHARA_URL)
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if response.status_code != 200:
            logging.debug("Docker Hub replied with status code %s.", response.status_code)
            raise HTTPConnectionError("Docker Hub replied with status code %s." % response.status_code)

        return filter(
            lambda x: not x['is_private'] and x['repository_type'] == 'image' and x['name'] not in EXCLUDED_IMAGES,
            response.json()['results']
        )

    @staticmethod
    def get_tagged_images() -> list[str]:
        """Returns the tagged names of all the active Kathara Docker on from Docker Hub.

        Returns:
            list[str]: A list of strings representing the tagged Docker images in the
                format "kathara/{image_name}:{tag}".

        Raises:
            HTTPConnectionError: If there is a connection error with the Docker Hub.
        """
        images = list(DockerHubApi.get_images())
        tagged_images = []

        def get_image_tag(tags, image):
            image_name = f"{image['namespace']}/{image['name']}"
            try:
                logging.debug(f"Getting Kathara tags for image '{image_name}' from Docker Hub...")
                response = requests.get(
                    f"https://hub.docker.com/v2/repositories/{image_name}/tags/?page_size=-1&ordering"
                )
            except requests.exceptions.ConnectionError as e:
                raise HTTPConnectionError(str(e))

            if response.status_code != 200:
                logging.debug(f"Docker Hub replied with status code %s for image '{image_name}'.", response.status_code)
                raise HTTPConnectionError(
                    f"Docker Hub replied with status code %s for image '{image_name}'." % response.status_code)

            tags.extend(list(map(
                lambda x: f"{image_name}:{x['name']}" if x['name'] != "latest" else image_name,
                filter(lambda x: x['tag_status'] == 'active', response.json()['results'])
            )))

        pool_size = get_pool_size()
        machines_pool = Pool(pool_size)

        items = chunk_list(images, pool_size)

        for chunk in items:
            machines_pool.map(func=partial(get_image_tag, tagged_images), iterable=chunk)

        return sorted(tagged_images)
