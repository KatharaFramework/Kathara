from ...ui.utils import confirmation_prompt
from ....manager.docker.DockerImage import DockerImage
from ....setting.Setting import Setting


class UpdateDockerImage(object):
    """Listener fired when there is a Docker Image update."""

    def run(self, docker_image: DockerImage, image_name: str) -> None:
        """Prompt the user for Docker Image Update.

        Args:
            docker_image (DockerImage): DockerImage instance.
            image_name (str): Name of the Docker image to update.

        Returns:
            None
        """
        policy = Setting.get_instance().image_update_policy
        if policy == 'Prompt':
            confirmation_prompt("A new version of image `%s` has been found on Docker Hub. "
                                "Do you want to pull it?" % image_name,
                                lambda: docker_image.pull(image_name),
                                lambda: None
                                )
        elif policy == 'Always':
            docker_image.pull(image_name)
