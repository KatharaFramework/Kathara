import logging
import mmap
import os
import re
from typing import List, Optional

from ...exceptions import MachineDependencyError
from ...trdparty.depgen import depgen


class DepParser(object):
    """Class responsible for parsing the lab.dep file."""

    @staticmethod
    def parse(path: str) -> Optional[List[str]]:
        """Parse the lab.dep file and return a List of string containing the names of the device ordered considering the
        dependencies.

        Args:
            path (str): The path to the lab.dep file.

        Returns:
            Optional[List[str]]: A List of string containing the names of the device ordered considering the
                dependencies.

        Raises:
            IOError: If there is an error while opening lab.dep file.
            SyntaxError: If there is a syntax error in lab.dep file.
            MachineDependencyError: If there is a Machines dependency loop in lab.dep file.
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
            if line and not line.startswith('#'):
                # E.g. MACHINE: MACHINE1 MACHINE2 MACHINE3
                # Or MACHINE:MACHINE1 MACHINE2 MACHINE3
                matches = re.search(r"^(?P<key>\w+):\s?(?P<deps>(\w+ ?)+)$",
                                    line
                                    )

                if matches:
                    key = matches.group("key").strip()
                    deps = list(map(lambda x: x.strip(), matches.group("deps").split(" ")))

                    # Dependencies are saved as dependencies[machine3] = [machine1, machine2]
                    dependencies[key] = deps
                else:
                    raise SyntaxError(f"[ERROR] In lab.dep - line {line_number}: Syntax error.")

            line_number += 1
            line = dep_mem_file.readline().decode('utf-8')

        if depgen.has_loop(dependencies):
            raise MachineDependencyError("Machines' dependency loop in lab.dep file.")

        return depgen.flatten(dependencies)
