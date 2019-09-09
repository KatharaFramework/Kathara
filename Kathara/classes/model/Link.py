
class Link(object):
    __slots__ = ['lab', 'name']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name

    def __repr__(self):
        return "Link(%s)" % self.name
