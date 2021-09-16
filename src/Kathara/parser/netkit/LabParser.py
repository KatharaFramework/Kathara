import mmap
import os
import re

from ...model.Lab import Lab


class LabParser(object):
    """
    Class responsible for parsing the lab.conf file.
    """

    @staticmethod
    def parse(path: str) -> Lab:
        """
        Parse the lab.conf and return the corresponding Kathara network scenario.

        Args:
            path (str): The path to lab.conf file.

        Returns:
            Kathara.model.Lab.Lab: A Kathara network scenario.
        """
        lab_conf_path = os.path.join(path, 'lab.conf')

        if not os.path.exists(lab_conf_path):
            raise FileNotFoundError("No lab.conf in given directory: %s\n" % path)

        # Reads lab.conf in memory so it is faster.
        with open(lab_conf_path, 'r') as lab_file:
            lab_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)

        lab = Lab(None, path=path)

        line_number = 1
        line = lab_mem_file.readline().decode('utf-8')
        while line:
            matches = re.search(r"^(?P<key>[a-z0-9_]{1,30})\[(?P<arg>\w+)\]=(?P<value>\".+\"|\'.+\'|\w+)$",
                                line.strip()
                                )

            if matches:
                key = matches.group("key").strip()
                arg = matches.group("arg").strip()
                value = matches.group("value").replace('"', '').replace("'", '')

                if key == "shared":
                    raise Exception("[ERROR] In line %d: "
                                    "`shared` is a reserved name, you can not use it for a device." % line_number)

                try:
                    # It's an interface, handle it.
                    interface_number = int(arg)

                    if re.search(r"^\w+$", value):
                        lab.connect_machine_to_link(key, value, machine_iface_number=interface_number)
                    else:
                        raise Exception("[ERROR] In line %d: "
                                        "Collision domain `%s` contains non-alphanumeric characters." % (line_number,
                                                                                                         value))
                except ValueError:
                    # Not an interface, add it to the machine metas.
                    lab.assign_meta_to_machine(key, arg, value)
            else:
                if not line.startswith('#') and \
                        line.strip():
                    if not line.startswith("LAB_NAME=") and \
                            not line.startswith("LAB_DESCRIPTION=") and \
                            not line.startswith("LAB_VERSION=") and \
                            not line.startswith("LAB_AUTHOR=") and \
                            not line.startswith("LAB_EMAIL=") and \
                            not line.startswith("LAB_WEB="):
                        raise Exception("[ERROR] In line %d: Invalid characters `%s`." % (line_number, line))
                    else:
                        (key, value) = line.split("=")
                        key = key.replace("LAB_", "").lower()
                        setattr(lab, key, value.replace('"', '').replace("'", '').strip())

            line_number += 1
            line = lab_mem_file.readline().decode('utf-8')

        lab.check_integrity()

        return lab
