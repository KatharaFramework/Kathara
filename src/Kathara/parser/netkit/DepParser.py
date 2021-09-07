import mmap
import os
import re
from typing import List, Union

from ...trdparty.depgen import depgen


class DepParser(object):
    @staticmethod
    def parse(path: str) -> Union[None, List[str]]:
        lab_dep_path = os.path.join(path, 'lab.dep')

        if not os.path.exists(lab_dep_path):
            return None

        dependencies = {}

        # Reads lab.dep in memory so it is faster.
        with open(lab_dep_path, 'r') as lab_file:
            dep_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)

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
