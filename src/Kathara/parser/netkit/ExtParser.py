import logging
import mmap
import os
import re
from typing import Dict, List, Optional

from ...model.ExternalLink import ExternalLink


class ExtParser(object):
    """
    Class responsible for parsing lab.ext file.
    """
    @staticmethod
    def parse(path: str) -> Optional[Dict[str, List[ExternalLink]]]:
        """
        Parse the lab.ext and return a Dict. Keys are name of collision domain and values are List of ExternalLink
        attached to that interface.

        Args:
            path (str): The path to lab.ext file.

        Returns:
            Optional[Dict[str, List[ExternalLink]]]: Keys are name of collision domain and values are List of
            ExternalLink attached to that interface.
        """
        lab_ext_path = os.path.join(path, 'lab.ext')

        if not os.path.exists(lab_ext_path):
            return None

        if os.stat(lab_ext_path).st_size == 0:
            logging.warning("lab.ext file is empty. Ignoring...")
            return None

        # Reads lab.ext in memory so it is faster.
        try:
            with open(lab_ext_path, 'r') as ext_file:
                ext_mem_file = mmap.mmap(ext_file.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            raise IOError("Cannot open lab.ext file.")

        external_links = {}

        line_number = 1
        line = ext_mem_file.readline().decode('utf-8')
        while line:
            # E.g. A enp9s0
            # B enp9s0.20
            matches = re.search(r"^(?P<link>\w+)\s+(?P<interface>\w+)(?P<vlan>\.\d+)?$",
                                line.strip()
                                )

            if matches:
                link = matches.group("link").strip()
                interface = matches.group("interface").strip()
                vlan = int(matches.group("vlan").strip().replace(".", "")) if matches.group("vlan") else None

                if vlan:
                    if 0 <= vlan >= 4095:
                        raise Exception("[ERROR] In file lab.ext, line %d: "
                                        "VLAN ID must be in range [1, 4094]." % line_number)

                if link not in external_links:
                    external_links[link] = []

                external_links[link].append(ExternalLink(interface, vlan))
            elif not line.startswith('#') and line.strip():
                raise Exception("[ERROR] In file lab.ext, line %d malformed." % line_number)

            line_number += 1
            line = ext_mem_file.readline().decode('utf-8')

        return external_links
