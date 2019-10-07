CURRENT_VERSION = "0.46.1"


def parse(version):
    l = [int(x, 10) for x in version.split('.')]
    l.reverse()
    return sum(x * (10 ** i) for i, x in enumerate(l))


def less_than(version, other_version):
    version = parse(version)
    other_version = parse(other_version)

    return version < other_version
