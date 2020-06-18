import logging
from docker.errors import APIError

from ...api.DockerHubApi import DockerHubApi
from ... import utils
from ...exceptions import HTTPConnectionError


class DockerImage(object):
    __slots__ = ['client']

    def __init__(self, client):
        self.client = client

    def check_local(self, image_name):
        return self.client.images.get(image_name)

    def pull(self, image_name):
        print("Pulling image `%s`... This may take a while." % image_name)
        tag = 'latest'
        img_name = image_name
        if ':' in image_name:
            split_name = image_name.split(':')
            img_name, tag = split_name[0], split_name[1]
        return self.client.images.pull(img_name, tag=tag)

    def check_update(self, image_name):
        logging.debug("Check update for %s" % image_name)
        local_image_info = self.check_local(image_name)

        # Image has been built locally, so there's nothing to compare.
        local_repo_digests = local_image_info.attrs["RepoDigests"]
        if not local_repo_digests:
            logging.debug("Image %s is build locally" % image_name)
            return

        try:
            remote_image_info = self.check_remote(image_name)
            local_repo_digest = local_repo_digests[0]
            remote_image_digest = remote_image_info["images"][0]["digest"]
        except HTTPConnectionError:
            logging.debug("Unable to connect to DockerHub")
            return

        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")

        if remote_image_digest != local_image_digest:
            utils.confirmation_prompt("A new version of image `%s` has been found on Docker Hub. "
                                      "Do you want to pull it?" % image_name,
                                      lambda: self.pull(image_name),
                                      lambda: None
                                      )

    def check_and_pull(self, image_name):
        try:
            # Tries to get the image from the local Docker repository.
            self.check_local(image_name)
            self.check_update(image_name)
        except APIError:
            # If not found, tries on Docker Hub.
            try:
                # If the image exists on Docker Hub, pulls it.
                self.check_remote(image_name)
                self.pull(image_name)
            except ConnectionError:
                raise ConnectionError("Image `%s` does not exists in local and not Internet connection for Docker Hub."
                                      % image_name)
            except Exception:
                raise Exception("Image `%s` does not exists neither in local nor on Docker Hub." % image_name)

    def multiple_check_and_pull(self, images):
        for image in images:
            self.check_and_pull(image)

    @staticmethod
    def check_remote(image_name):
        return DockerHubApi.get_image_information(image_name)
