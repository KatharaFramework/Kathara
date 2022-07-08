from __future__ import annotations

from typing import List, Optional

from docker.types import Mount

from ... import utils


class InceptionManager(object):
    __slots__ = ['mount_volumes']

    __instance: InceptionManager = None

    @staticmethod
    def get_instance() -> InceptionManager:
        """Get an instance of the Inception Manager.

        Returns:
            Inception: instance of the Inception Manager.
        """
        if InceptionManager.__instance is None:
            InceptionManager()

        return InceptionManager.__instance

    def __init__(self) -> None:
        if InceptionManager.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.mount_volumes: List[Mount] = [
                Mount(target="/var/lib/docker/overlay2", source="/var/lib/docker/overlay2", type="bind"),
                Mount(target="/var/lib/docker/image", source="/var/lib/docker/image", type="bind")
            ]

            InceptionManager.__instance = self

    def get_mount_volumes(self) -> Optional[List[Mount]]:
        if utils.is_running_in_container():
            return self.mount_volumes

        return None
