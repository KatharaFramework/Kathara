import logging
import mmap
import os
import re

from ...exceptions import LinkModeError
from ...model.Lab import Lab, LAB_METADATA
from ...utils import parse_interface_definition, RESERVED_MACHINE_NAMES

CD_MODE_REGEX = re.compile(r"^CD_MODE\[(?P<cd>\w+)\]=([\"\']?)(?P<value>[^\"\']+?)(\2)(\s+\#.*)?$")


class LabParser(object):
    """Class responsible for parsing the lab.conf file."""

    @staticmethod
    def parse(path: str, conf_name: str = "lab.conf") -> Lab:
        """Parse the lab configuration identified by conf_name and return the corresponding Kathara network scenario.

        Args:
            path (str): The path to the directory containing the configuration file.
            conf_name (str): The name of the network scenario configuration file (default is 'lab.conf').

        Returns:
            Kathara.model.Lab.Lab: A Kathara network scenario.
        """
        lab_conf_path = os.path.join(path, conf_name)

        if not os.path.exists(lab_conf_path):
            raise IOError(f"No {conf_name} in given directory.")

        if os.stat(lab_conf_path).st_size == 0:
            raise IOError(f"{conf_name} file is empty.")

        # Reads lab.conf in memory, so it is faster.
        try:
            with open(lab_conf_path, 'r') as lab_file:
                lab_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            raise IOError(f"Cannot open {conf_name} file.")

        lab = Lab(None, path=path)
        # The modes of the collision domains, applied when all the devices are known
        cd_modes = {}

        line_number = 1
        line = lab_mem_file.readline().decode('utf-8')
        while line:
            matches = re.search(
                r"^(?P<key>[a-z0-9_]{1,30})\[(?P<arg>\w+)\]=([\"\']?)(?P<value>[^\"\']+)(\3)(\s+\#.*)?$",
                line.strip()
            )

            if matches:
                key = matches.group("key").strip()
                arg = matches.group("arg").strip()
                value = matches.group("value").replace('"', '').replace("'", '')

                if key in RESERVED_MACHINE_NAMES:
                    raise ValueError(f"In {conf_name} - Line {line_number}: "
                                     f"`{key}` is a reserved name, you can not use it for a device.")

                try:
                    # It's an interface, handle it.
                    interface_number = int(arg)

                    try:
                        cd_name, mac_address, vlans = parse_interface_definition(value)
                    except SyntaxError as e:
                        raise SyntaxError(f"In {conf_name} - Line {line_number}: {str(e)}")

                    if re.search(r"^\w+$", cd_name):
                        lab.connect_machine_to_link(key, cd_name,
                                                    machine_iface_number=interface_number, mac_address=mac_address,
                                                    **vlans)
                    else:
                        raise SyntaxError(f"In {conf_name} - Line {line_number}: "
                                          f"Collision domain `{value}` contains non-alphanumeric characters.")
                except ValueError:
                    # Not an interface, add it to the machine metas.
                    if lab.assign_meta_to_machine(key, arg, value) is not None:
                        logging.warning(f"In {conf_name} - Line {line_number}: "
                                        f"Device `{key}` already has a value assigned to meta `{arg}`. "
                                        f"Previous value has been overwritten with `{value}`.")
            elif CD_MODE_REGEX.search(line.strip()):
                # It's the mode of a collision domain, the last value is kept.
                matches = CD_MODE_REGEX.search(line.strip())
                cd_modes[matches.group("cd")] = (matches.group("value").strip(), line_number)
            else:
                if not line.startswith('#') and \
                        line.strip():
                    if not any([line.startswith(f"{x}=") for x in LAB_METADATA]):
                        raise SyntaxError(f"In {conf_name} - Line {line_number}: `{line}`.")
                    else:
                        (key, value) = line.split("=")
                        key = key.replace("LAB_", "").lower()
                        setattr(lab, key, value.replace('"', '').replace("'", '').strip())

            line_number += 1
            line = lab_mem_file.readline().decode('utf-8')

        for cd_name, (cd_mode, cd_line_number) in cd_modes.items():
            if not lab.has_link(cd_name):
                raise SyntaxError(f"In {conf_name} - Line {cd_line_number}: "
                                  f"Collision domain `{cd_name}` is not used by any device.")

            try:
                lab.get_link(cd_name).mode = cd_mode
            except LinkModeError as e:
                raise SyntaxError(f"In {conf_name} - Line {cd_line_number}: {str(e)}")

        lab.check_integrity()

        return lab
