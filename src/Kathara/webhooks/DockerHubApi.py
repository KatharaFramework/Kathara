import logging
from multiprocessing.dummy import Pool

import requests

from ..exceptions import HTTPConnectionError
from ..utils import get_pool_size

DOCKER_HUB_KATHARA_IMAGES_URL: str = "https://hub.docker.com/v2/repositories/kathara/?page_size=-1"
DOCKER_HUB_KATHARA_TAGS_URL: str = "https://hub.docker.com/v2/repositories/{image_name}/tags/?page_size=-1&ordering"
REQUEST_TIMEOUT: int = 1

EXCLUDED_IMAGES: list[str] = ['megalos-bgp-manager', 'kathara', 'kathara-lab-checker']


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
            response = requests.get(DOCKER_HUB_KATHARA_IMAGES_URL, timeout=(REQUEST_TIMEOUT, REQUEST_TIMEOUT))
        except requests.exceptions.Timeout as e:
            raise HTTPConnectionError(str(e))
        except requests.exceptions.ConnectionError as e:
            raise HTTPConnectionError(str(e))

        if response.status_code != 200:
            logging.debug(f"Docker Hub replied with status code {response.status_code}.")
            raise HTTPConnectionError(f"Docker Hub replied with status code {response.status_code}.")

        return filter(
            lambda x: not x['is_private'] and 'image' in x['content_types'] and x['name'] not in EXCLUDED_IMAGES,
            response.json()['results']
        )

    @staticmethod
    def get_tagged_images() -> list[str]:
        """Returns the list of available Kathara images on Docker Hub with all the active tags.

        Returns:
            list[str]: A list of strings representing the tagged Docker images in the
                format "kathara/{image_name}:{tag}".

        Raises:
            HTTPConnectionError: If there is a connection error with the Docker Hub.
        """
        images = list(DockerHubApi.get_images())
        tagged_images = []

        def get_image_tag(image):
            image_name = f"{image['namespace']}/{image['name']}"
            try:
                logging.debug(f"Getting tags for image `{image_name}` from Docker Hub...")
                response = requests.get(
                    DOCKER_HUB_KATHARA_TAGS_URL.format(image_name=image_name),
                    timeout=(REQUEST_TIMEOUT, REQUEST_TIMEOUT)
                )
            except requests.exceptions.Timeout as e:
                raise HTTPConnectionError(str(e))
            except requests.exceptions.ConnectionError as e:
                raise HTTPConnectionError(str(e))

            if response.status_code != 200:
                logging.debug(
                    f"Error while retrieving tags for image `{image_name}. "
                    f"Docker Hub replied with status code {response.status_code}."
                )
                raise HTTPConnectionError(
                    f"Error while retrieving tags for image `{image_name}`. "
                    f"Docker Hub replied with status code {response.status_code}."
                )

            tagged_images.extend(list(map(
                lambda x: f"{image_name}:{x['name']}" if x['name'] != "latest" else image_name,
                filter(lambda x: x['tag_status'] == 'active', response.json()['results'])
            )))

        pool_size = get_pool_size()
        with Pool(pool_size) as tags_pool:
            tags_pool.map(func=get_image_tag, iterable=images)

        return sorted(tagged_images)
