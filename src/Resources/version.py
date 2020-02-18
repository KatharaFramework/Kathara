CURRENT_VERSION = "2.2.2"


def parse(version):
    return tuple([int(x) for x in version.split('.')])


def less_than(version, other_version):
    version = parse(version)
    other_version = parse(other_version)

    return version < other_version
