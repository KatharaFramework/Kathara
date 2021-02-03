import mmap
import os
import re

from ...model.Lab import Lab
from ...manager.docker import DockerManager
from ...utils import check_value,getHostname
class LabParser(object):
    
    @staticmethod
    def parse(path):
        lab_conf_path = os.path.join(path, 'lab.conf')

        if not os.path.exists(lab_conf_path):
            raise FileNotFoundError("No lab.conf in given directory: %s\n" % path)

        # Reads lab.conf in memory so it is faster.
        with open(lab_conf_path, 'r') as lab_file:
            lab_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)

        lab = Lab(path)

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
                                    "`shared` is a reserved name, you can not use it for a machine." % line_number)

                try:
                    # It's an interface, handle it.
                    interface_number = int(arg)
                    if re.search(r"^\w+$", value) or check_value(value):
                        if re.search(r"^\w+$", value):
                            if getHostname() == '.':
                                lab.connect_machine_to_link(key, interface_number, value+getHostname())
                            else:
                                lab.connect_machine_to_link(key, interface_number, value+'.'+getHostname())
                        else:
                            lab.connect_machine_to_link(key, interface_number, value)
                    else:
                        raise Exception("[ERROR] In line %d: "
                                        "Link `%s` contains non-alphanumeric characters." % (line_number, value))
                except ValueError:
                    # Not an interface, add it to the machine metas.
                    lab.assign_meta_to_machine(key, arg, value)
            else:
                if not line.startswith('#') and \
                        line.strip():
                    if not line.startswith("LAB_DESCRIPTION=") and \
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

