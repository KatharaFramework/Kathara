import requests

DOCKER_HUB_IMAGE_URL = "https://hub.docker.com/v2/repositories/%s/tags/latest/"


class DockerHubApi(object):
    @staticmethod
    def get_image_information(image_name):
        result = requests.get(DOCKER_HUB_IMAGE_URL % image_name)

        if result.status_code != 200:
            raise Exception()

        return result.json()
