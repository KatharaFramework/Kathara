import logging

from docker.errors import APIError

from ... import utils


class DockerImage(object):
    __slots__ = ['client']

    def __init__(self, client):
        self.client = client

    def get_local(self, image_name):
        return self.client.images.get(image_name)

    def get_remote(self, image_name):
        return self.client.images.get_registry_data(image_name)

    def pull(self, image_name):
        # If no tag or sha key is specified, we add "latest"
        if (':' or '@') not in image_name:
            image_name = "%s:latest" % image_name

        logging.info("Pulling image `%s`... This may take a while." % image_name)
        return self.client.images.pull(image_name)

    def check_for_updates(self, image_name):
        logging.debug("Checking updates for %s..." % image_name)

        if '@' in image_name:
            logging.debug('No need to check image digest of %s' % image_name)
            return

        local_image_info = self.get_local(image_name)
        # Image has been built locally, so there's nothing to compare.
        local_repo_digests = local_image_info.attrs["RepoDigests"]
        if not local_repo_digests:
            logging.debug("Image %s is build locally" % image_name)
            return

        remote_image_info = self.get_remote(image_name).attrs['Descriptor']
        local_repo_digest = local_repo_digests[0]
        remote_image_digest = remote_image_info["digest"]

        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")
        # We only need to update tagged images, not the ones with digests.
        if remote_image_digest != local_image_digest:
            utils.confirmation_prompt("A new version of image `%s` has been found on Docker Hub. "
                                      "Do you want to pull it?" % image_name,
                                      lambda: self.pull(image_name),
                                      lambda: None
                                      )

    def check_and_pull(self, image_name):
        try:
            # Tries to get the image from the local Docker repository.
            self.get_local(image_name)
            self.check_for_updates(image_name)
        except APIError:
            # If not found, tries on Docker Hub.
            try:
                # If the image exists on Docker Hub, pulls it.
                self.get_remote(image_name)
                self.pull(image_name)
            except ConnectionError:
                raise ConnectionError("Image `%s` does not exists in local and no Internet connection for Docker Hub."
                                      % image_name)
            except Exception:
                raise Exception("Image `%s` does not exists either in local or on Docker Hub." % image_name)

    def check_and_pull_from_list(self, images):
        for image in images:
            self.check_and_pull(image)
