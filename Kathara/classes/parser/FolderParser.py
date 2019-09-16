from glob import glob
import os

from ..model.Lab import Lab


class FolderParser(object):
    @staticmethod
    def parse(path):
        lab = Lab(path)

        machine_folders = glob(path + "/*/")

        for machine_folder in machine_folders:
            # Get tail of the path, :-1 is required to remove the trailing slash
            # Otherwise basename will return an empty string
            machine_name = os.path.basename(machine_folder[:-1])

            if machine_name == "shared":
                continue

            lab.get_or_new_machine(machine_name)

        return lab
