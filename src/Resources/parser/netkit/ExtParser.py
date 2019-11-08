import mmap
import os
import re

from ...model.ExternalLink import ExternalLink


class ExtParser(object):
    @staticmethod
    def parse(path):
        lab_ext_path = os.path.join(path, 'lab.ext')

        if not os.path.exists(lab_ext_path):
            return

        # Reads lab.ext in memory so it is faster.
        with open(lab_ext_path, 'r') as ext_file:
            ext_mem_file = mmap.mmap(ext_file.fileno(), 0, access=mmap.ACCESS_READ)

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

                if link not in external_links:
                    external_links[link] = []

                external_links[link].append(ExternalLink(interface, vlan))

            line_number += 1
            line = ext_mem_file.readline().decode('utf-8')

        return external_links

        # if eth0 => add eth0 to bridge
        # if eth0.VLAN =>
        #   $(ip link add link $PREFIX_INTERFACE name $INTERFACE type vlan id $VLAN)
        #   $(ip link set dev $INTERFACE up)
        #   $(brctl addif br-$BRCTL_NET $INTERFACE)

        # Clean