import logging
import mmap
import os
import re
from typing import Set, Dict, Tuple, List

from ...model.ExternalLink import ExternalLink
from ...types import CollisionDomainTypesOption

SUPPORTED_ARGS: Set[str] = {"external", "type"}

LINE_REGEX = re.compile(r"^(?P<name>\w+)\[(?P<arg>\w+)\]=([\"\']?)(?P<value>[^\"\']+)(\3)(\s+\#.*)?$")
# E.g. enp9s0 or enp9s0.20
EXTERNAL_IFACE_REGEX = re.compile(r"^(?P<interface>\w+)(?P<vlan>\.\d+)?$")


class LinkParser(object):
    """Class responsible for parsing lab.link file."""

    @staticmethod
    def parse(path: str) -> Tuple[Dict[str, str], Dict[str, List[ExternalLink]]]:
        lab_link_path = os.path.join(path, 'lab.link')

        if not os.path.exists(lab_link_path):
            raise FileNotFoundError(f"lab.link file does not exist.")

        if os.stat(lab_link_path).st_size == 0:
            logging.warning("lab.link file is empty. Ignoring...")
            return {}, {}

        # Reads lab.link in memory so it is faster.
        try:
            with open(lab_link_path, 'r') as link_file:
                link_mem_file = mmap.mmap(link_file.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            raise IOError("Cannot open lab.link file.")

        link_types = {}
        external_links = {}

        line_number = 1
        line = link_mem_file.readline().decode('utf-8')
        while line:
            matches = LINE_REGEX.fullmatch(line.strip())

            if matches:
                name = matches.group('name')
                arg = matches.group('arg')
                value = matches.group('value')

                if arg not in SUPPORTED_ARGS:
                    raise SyntaxError(
                        f"In lab.link - Line {line_number}: "
                        f"Invalid argument `{arg}`. "
                        f"Supported arguments are {', '.join(SUPPORTED_ARGS)}."
                    )

                if arg == "type":
                    try:
                        link_type = CollisionDomainTypesOption.parse(value)
                    except ValueError as e:
                        raise SyntaxError(f"In lab.link - Line {line_number}: {e}")

                    if name in link_types:
                        logging.warning(
                            f"In lab.link - Line {line_number}: "
                            f"Collision domain `{name}` already has a type assigned. "
                            f"Previous value has been overwritten with `{value}`."
                        )

                    link_types[name] = link_type
                elif arg == "external":
                    ext_matches = EXTERNAL_IFACE_REGEX.fullmatch(value.strip())
                    if ext_matches:
                        interface = ext_matches.group("interface").strip()
                        vlan = int(ext_matches.group("vlan").replace(".", "")) if ext_matches.group("vlan") else None

                        try:
                            external_link = ExternalLink(interface, vlan)
                        except ValueError as e:
                            raise ValueError(f"In file lab.link, line {line_number}: {e}")

                        if name not in external_links:
                            external_links[name] = []

                        external_links[name].append(external_link)
                    else:
                        raise SyntaxError(f"In file lab.link - Line {line_number}.")
            elif not line.startswith('#') and line.strip():
                raise SyntaxError(f"In file lab.link - Line {line_number}.")

            line_number += 1
            line = link_mem_file.readline().decode('utf-8')

        return link_types, external_links
