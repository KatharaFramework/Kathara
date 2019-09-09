import os
import collections


class Machine(object):
    __slots__ = ['lab', 'name', 'startup_path', 'shutdown_path', 'folder', 'interfaces', 'meta']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name

        startup_file = os.path.join(lab.path, '%s.startup' % self.name)
        self.startup_path = startup_file if os.path.exists(startup_file) else None

        shutdown_file = os.path.join(lab.path, '%s.shutdown' % self.name)
        self.shutdown_path = shutdown_file if os.path.exists(shutdown_file) else None

        machine_folder = os.path.join(lab.path, '%s' % self.name)
        self.folder = machine_folder if os.path.isdir(machine_folder) else None

        self.interfaces = {}
        self.meta = {}

    def add_interface(self, number, link):
        if number in self.interfaces:
            raise Exception("Interface %d already set on machine `%s`." % (number, self.name))

        self.interfaces[number] = link

    def add_meta(self, name, value):
        self.meta[name] = value

    def check(self):
        """
        Sorts the dictionary of interfaces ignoring the missing positions
        """
        sorted_interfaces = sorted(self.interfaces.items(), key=lambda kv: kv[0])

        for i in range(1, len(sorted_interfaces)):
            if sorted_interfaces[i - 1][0] != sorted_interfaces[i][0] - 1:
                # If a number is non sequential, the rest of the list is garbage.
                # Throw it away.
                sorted_interfaces = sorted_interfaces[:i]
                break

        self.interfaces = collections.OrderedDict(sorted_interfaces)

    def __repr__(self):
        return "Machine(%s, %s)" % (self.name, self.interfaces)
