from typing import Tuple

CURRENT_VERSION = "3.7.0"


def parse(version: str) -> Tuple:
    return tuple([int(x) for x in version.split('.')])


def less_than(version: str, other_version: str) -> bool:
    version = parse(version)
    other_version = parse(other_version)

    return version < other_version
