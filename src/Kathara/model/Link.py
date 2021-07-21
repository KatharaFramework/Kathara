BRIDGE_LINK_NAME = "kathara_host_bridge"


class Link(object):
    """
     A Kathara collision domain. Contains information about the collision domain and
     the API object to interact with the manager.

     Attributes:
         lab (Kathara.model.Lab): The Kathara network Scenario of the collision domain.
         name (str): The name of the collision domain.
         external (List[Kathara.model.ExternalLink]): List of the ExternalLinks attached to this collision domain.
         api_object (Any): To interact with the current Kathara manager.
    """
    __slots__ = ['lab', 'name', 'external', 'api_object']

    def __init__(self, lab, name):
        self.lab = lab
        """"""
        self.name = name
        self.external = []

        self.api_object = None

    def __repr__(self):
        return "Link(%s, %s)" % (self.name, self.external)
