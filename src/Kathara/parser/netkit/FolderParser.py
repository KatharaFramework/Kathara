import os
from glob import glob

from ...model.Lab import Lab
from ...utils import RESERVED_MACHINE_NAMES


class FolderParser(object):
    """
    Class responsible for parsing the folder in the network scenario directory.
    """
    @staticmethod
    def parse(path: str) -> Lab:
        """
        Parse the network scenario folders and return a network scenario containing the corresponding devices.

        Args:
            path (str): The path to the network scenario directory.

        Returns:
            Kathara.model.Lab.Lab: A Kathara network scenario.
        """
        lab = Lab(None, path=path)

        # Get all subfolders of lab path
        machine_folders = glob("%s/*/" % path)

        for machine_folder in machine_folders:
            # Get tail of the path, :-1 is required to remove the trailing slash
            # Otherwise basename will return an empty string
            machine_name = os.path.basename(machine_folder[:-1])

            # Shared is a reserved name, ignore it.
            if machine_name in RESERVED_MACHINE_NAMES:
                continue

            lab.get_or_new_machine(machine_name)

        return lab
