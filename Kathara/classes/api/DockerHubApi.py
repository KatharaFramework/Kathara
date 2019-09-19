import requests

DOCKER_HUB_IMAGE_URL = "https://cloud.docker.com/v2/repositories/"


class DockerHubApi(object):
    @staticmethod
    def get_image_information(image_name):
        result = requests.get(DOCKER_HUB_IMAGE_URL + image_name)

        if result.status_code != 200:
            raise Exception()

        return result.json
