import io
import logging
import os
import tarfile
import tempfile
from typing import Union, List, Set, Iterator

import docker.models.containers
import docker.models.images
from docker import DockerClient
from docker.errors import APIError, ImageNotFound

from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import InvalidImageArchitectureError, DockerImageNotFoundError


class DockerImage(object):
    """Class responsible for interacting with Docker Images."""
    __slots__ = ['client']

    def __init__(self, client: DockerClient) -> None:
        self.client: DockerClient = client

    def get_local(self, image_name: str) -> docker.models.images.Image:
        """Return the specified Docker Image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            docker.models.images.Image: A Docker Image
        """
        return self.client.images.get(image_name)

    def get_remote(self, image_name: str) -> docker.models.images.RegistryData:
        """Gets the registry data for an image.

        Args:
            image_name (str): The name of the image.

        Returns:
            docker.models.images.RegistryData: The data object.

        Raises:
            `docker.errors.APIError`: If the server returns an error.
        """
        return self.client.images.get_registry_data(image_name)

    def pull(self, image_name: str) -> None:
        """Pull the specified Docker Image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            None
        """
        # If no tag or sha key is specified, we add "latest"
        if (':' or '@') not in image_name:
            image_name = "%s:latest" % image_name

        EventDispatcher.get_instance().dispatch("docker_pull_started")
        logging.info("Pulling image `%s`... This may take a while." % image_name)
        response = self.client.api.pull(image_name, stream=True, decode=True)
        for progress in response:
            EventDispatcher.get_instance().dispatch("docker_pull_progress", progress=progress)
        EventDispatcher.get_instance().dispatch("docker_pull_ended")

    def commit_container(self, container: docker.models.containers.Container, repository: str,
                         tag: str = "latest") -> str:
        """Commit a running container into a new local Docker image, capturing its filesystem state.

        Args:
            container (docker.models.containers.Container): The container to commit.
            repository (str): The repository name to assign to the committed image.
            tag (str): The tag to assign to the committed image. Default is "latest".

        Returns:
            str: The reference (`repository:tag`) of the committed image.
        """
        image_ref = f"{repository}:{tag}"
        logging.debug(f"Committing container `{container.name}` into image `{image_ref}`...")

        # Drop a stale image with the same reference from a previous save, if any.
        self.remove_image(image_ref)
        container.commit(repository=repository, tag=tag)

        return image_ref

    def save_image_to_tar(self, image_name: str) -> Iterator[bytes]:
        """Export a local Docker image as a tar stream (equivalent to `docker image save`).

        Args:
            image_name (str): The name of the local Docker image to export.

        Returns:
            Iterator[bytes]: A generator streaming the image tarball content.
        """
        logging.debug(f"Saving image `{image_name}` to tar...")
        return self.client.images.get(image_name).save(named=True)

    def load_images_from_tar(self, tar_stream: Union[bytes, Iterator[bytes]]) -> None:
        """Load one or more Docker images from a tar stream (equivalent to `docker image load`).

        Args:
            tar_stream (Union[bytes, Iterator[bytes]]): The image tarball content.

        Returns:
            None
        """
        logging.debug("Loading images from tar...")
        self.client.images.load(tar_stream)

    def build_image_from_diff(self, base_image: str, tag: str, diff_tar_path: str,
                              deletions: List[str]) -> docker.models.images.Image:
        """Reconstruct an image from a base image plus a filesystem-diff tarball.

        Builds an image equivalent to `base_image` with the saved changes applied: the diff tarball
        (added/modified files) is extracted on top, and the recorded deletions are removed.

        Args:
            base_image (str): The base image to build upon.
            tag (str): The tag to assign to the reconstructed image.
            diff_tar_path (str): Path to the filesystem-diff tarball (added/modified files).
            deletions (List[str]): Absolute paths removed relative to the base image.

        Returns:
            docker.models.images.Image: The reconstructed image.
        """
        dockerfile_lines = [f"FROM {base_image}", "ADD diff.tar /"]
        if deletions:
            # Single-quote each path for the shell, escaping embedded single quotes.
            quoted = " ".join("'%s'" % p.replace("'", "'\\''") for p in deletions)
            dockerfile_lines.append(f"RUN rm -rf {quoted}")
        dockerfile = ("\n".join(dockerfile_lines) + "\n").encode("utf-8")

        logging.debug(f"Reconstructing image `{tag}` from base `{base_image}`...")

        # Assemble the build context (Dockerfile + diff.tar) on disk to avoid loading it into memory.
        ctx_fd, ctx_path = tempfile.mkstemp(prefix="kathara_ctx_", suffix=".tar")
        try:
            with os.fdopen(ctx_fd, "wb") as ctx_file:
                with tarfile.open(fileobj=ctx_file, mode="w") as ctx_tar:
                    info = tarfile.TarInfo("Dockerfile")
                    info.size = len(dockerfile)
                    ctx_tar.addfile(info, io.BytesIO(dockerfile))
                    ctx_tar.add(diff_tar_path, arcname="diff.tar")

            with open(ctx_path, "rb") as ctx_file:
                image, _ = self.client.images.build(
                    fileobj=ctx_file, custom_context=True, tag=tag, rm=True, forcerm=True, pull=False
                )
            return image
        finally:
            os.remove(ctx_path)

    def remove_image(self, image_name: str) -> None:
        """Remove a local Docker image, ignoring the error if it does not exist.

        Args:
            image_name (str): The name of the local Docker image to remove.

        Returns:
            None
        """
        try:
            self.client.images.remove(image_name, force=True)
        except ImageNotFound:
            logging.debug(f"Image `{image_name}` not found, skipping removal.")

    def check_for_updates(self, image_name: str) -> None:
        """Update the specified image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            None
        """
        logging.debug(f"Checking updates for {image_name}...")

        if '@' in image_name:
            logging.debug(f"No need to check image digest of {image_name}.")
            return

        local_image_info = self.get_local(image_name)
        # Image has been built locally, so there's nothing to compare.
        local_repo_digests = local_image_info.attrs["RepoDigests"]
        if not local_repo_digests:
            logging.debug(f"Image {image_name} is built locally.")
            return

        remote_image_info = self.get_remote(image_name).attrs['Descriptor']
        local_repo_digest = local_repo_digests[0]
        remote_image_digest = remote_image_info["digest"]

        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")
        # We only need to update tagged images, not the ones with digests.
        if remote_image_digest != local_image_digest:
            EventDispatcher.get_instance().dispatch("docker_image_update_found",
                                                    docker_image=self,
                                                    image_name=image_name)

    def check(self, image_name: str) -> None:
        """Check the existence of the specified image.

        Args:
            image_name (str): The name of a Docker Image.

        Returns:
            None

        Raises:
            ConnectionError: If there is a connection error while pulling the Docker image from Docker Hub.
            DockerImageNotFoundError: If the Docker image is not available neither on Docker Hub nor in local repository.
        """
        self._check_and_pull(image_name, pull=False)

    def check_from_list(self, images: Union[List[str], Set[str]]) -> None:
        """Check a list of specified images.

        Args:
            images (Union[List[str], Set[str]]): A list of Docker images name to pull.

        Returns:
            None
        """
        for image in images:
            self._check_and_pull(image)

    def _check_and_pull(self, image_name: str, pull: bool = True) -> None:
        """Check and pull of the specified image.

        Args:
            image_name (str): The name of a Docker Image.
            pull (bool): If True, pull the image from Docker Hub.

        Returns:
            None

        Raises:
            ConnectionError: If there is a connection error while pulling the Docker image from Docker Hub.
            DockerImageNotFoundError: If the Docker image is not available neither on Docker Hub
                nor in local repository.
            InvalidImageArchitectureError: If the Docker image is not compatible with the host architecture.
        """
        try:
            # Tries to get the image from the local Docker repository.
            image = self.get_local(image_name)
            self._check_image_architecture(image_name, image)
            try:
                if pull:
                    self.check_for_updates(image_name)
            except APIError:
                logging.debug("Cannot check updates, skipping...")
        except InvalidImageArchitectureError as e:
            raise e
        except APIError:
            # If not found, tries on Docker Hub.
            try:
                # If the image exists on Docker Hub, pulls it.
                registry_data = self.get_remote(image_name)
                self._check_image_architecture(image_name, registry_data)
                if pull:
                    self.pull(image_name)
            except APIError as e:
                if e.response.status_code == 500 and 'dial tcp' in e.explanation:
                    raise ConnectionError(
                        f"Docker Image `{image_name}` is not available in local repository and "
                        "no Internet connection is available to pull it from Docker Hub."
                    )
                else:
                    raise DockerImageNotFoundError(image_name)
            except InvalidImageArchitectureError as e:
                raise e

    @staticmethod
    def _check_image_architecture(image_name: str,
                                  image: Union[docker.models.images.Image, docker.models.images.RegistryData]) -> None:
        """Check if the specified image is compatible with the host architecture.

        Args:
            image_name (str): The name of the Docker Image to check.
            image (Union[docker.models.images.Image, docker.models.images.RegistryData]): Docker Image object.

        Returns:
            None
            
        Raises: 
            InvalidImageArchitectureError: If the Docker image is not compatible with the architecture.
        """
        host_arch = utils.get_architecture()

        # amd64 images are compatible on macOS using Rosetta.
        compatible_archs = utils.exec_by_platform(
            lambda: {host_arch}, lambda: {host_arch}, lambda: {host_arch, "amd64"}
        )

        logging.debug(f"Platform compatible architectures: {compatible_archs}")

        is_compatible = False
        if isinstance(image, docker.models.images.Image):
            is_compatible = image.attrs['Architecture'] in compatible_archs
        elif isinstance(image, docker.models.images.RegistryData):
            image_archs = list(
                filter(lambda x: x['architecture'] in compatible_archs, image.attrs['Platforms'])
            )
            is_compatible = len(image_archs) > 0
            logging.debug(f"Found compatible architectures: {image_archs}")

        if not is_compatible:
            raise InvalidImageArchitectureError(image_name, host_arch)
