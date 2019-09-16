import mmap
import os
import re
import sys

from ..trdparty.depgen import depgen


class DepParser(object):
    @staticmethod
    def parse(path):
        lab_dep_path = os.path.join(path, 'lab.dep')

        if not os.path.exists(lab_dep_path):
            return None

        dependencies = {}

        # Reads lab.dep in memory so it is faster.
        with open(lab_dep_path, 'r') as lab_file:
            dep_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)

        line = dep_mem_file.readline().decode('utf-8')
        while line:
            # E.g. MACHINE: MACHINE1 MACHINE2 MACHINE3
            # Or MACHINE:MACHINE1 MACHINE2 MACHINE3
            matches = re.search(r"^(?P<key>\w+): ?(?P<deps>(\w+ ?)+)$",
                                line.strip()
                                )

            if matches:
                key = matches.group("key").strip()
                deps = matches.group("deps").strip().split(" ")

                # Dependencies are saved as dependencies[machine3] = [machine1, machine2]
                dependencies[key] = deps

            line = dep_mem_file.readline().decode('utf-8')

        if depgen.has_loop(dependencies):
            sys.stderr.write("WARNING: loop in lab.dep, it will be ignored.\n")
            return None

        return depgen.flatten(dependencies)
