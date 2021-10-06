import logging
import mmap
import os
import re
from typing import List, Optional

from ...trdparty.depgen import depgen


class DepParser(object):
    """
    Class responsible for parsing the lab.dep file.
    """
    @staticmethod
    def parse(path: str) -> Optional[List[str]]:
        """
        Parse the lab.dep file and return a List of string containing the names of the device ordered considering the
        dependencies.

        Args:
            path (str): The path to the lab.dep file.

        Returns:
            Optional[List[str]]: A List of string containing the names of the device ordered considering the
            dependencies.
        """
        lab_dep_path = os.path.join(path, 'lab.dep')

        if not os.path.exists(lab_dep_path):
            return None

        if os.stat(lab_dep_path).st_size == 0:
            logging.warning("lab.dep file is empty. Ignoring...")
            return None

        dependencies = {}

        # Reads lab.dep in memory so it is faster.
        try:
            with open(lab_dep_path, 'r') as dep_file:
                dep_mem_file = mmap.mmap(dep_file.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            raise IOError("Cannot open lab.dep file.")

        line_number = 1
        line = dep_mem_file.readline().decode('utf-8')
        while line:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # E.g. MACHINE: MACHINE1 MACHINE2 MACHINE3
            # Or MACHINE:MACHINE1 MACHINE2 MACHINE3
            matches = re.search(r"^(?P<key>\w+):\s?(?P<deps>(\w+ ?)+)$",
                                line
                                )

            if matches:
                key = matches.group("key").strip()
                deps = matches.group("deps").strip().split(" ")

                # Dependencies are saved as dependencies[machine3] = [machine1, machine2]
                dependencies[key] = deps
            else:
                raise Exception("[ERROR] In lab.dep - line %d: Syntax error." % line_number)

            line_number += 1
            line = dep_mem_file.readline().decode('utf-8')

        if depgen.has_loop(dependencies):
            raise Exception("ERROR: Loop in lab.dep.\n")

        return depgen.flatten(dependencies)
