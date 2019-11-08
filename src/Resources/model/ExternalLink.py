class ExternalLink(object):
    __slots__ = ['interface', 'vlan']

    def __init__(self, interface, vlan):
        self.interface = interface
        self.vlan = vlan

    def get_name(self):
        return "%s.%s" % (self.interface, self.vlan) if self.vlan else self.interface

    def __repr__(self):
        return "ExternalLink(%s, %s)" % (self.interface, self.vlan)
