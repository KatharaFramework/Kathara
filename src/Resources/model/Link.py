BRIDGE_LINK_NAME = "kathara_host_bridge"


class Link(object):
    __slots__ = ['lab', 'name', 'external', 'api_object']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name
        self.external = []

        self.api_object = None

    def __repr__(self):
        return "Link(%s, %s)" % (self.name, self.external)
