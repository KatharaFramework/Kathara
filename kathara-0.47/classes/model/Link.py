BRIDGE_LINK_NAME = "docker_bridge"


class Link(object):
    __slots__ = ['lab', 'name', 'api_object']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name
        self.api_object = None

    def __repr__(self):
        return "Link(%s)" % self.name
