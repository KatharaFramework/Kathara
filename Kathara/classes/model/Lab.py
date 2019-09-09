import utils

from classes.model.Machine import Machine
from classes.model.Link import Link


class Lab(object):
    __slots__ = ['description', 'version', 'author', 'email', 'web',
                 'machines', 'links', 'net_counter', 'folder_hash', 'path',
                 'shared_startup_path', 'shared_shutdown_path']

    def __init__(self, path):
        self.path = path
        self.folder_hash = utils.generate_urlsafe_hash(path)

        self.machines = {}
        self.links = {}

        return

    def connect_machine_to_link(self, machine_name, machine_iface_number, link_name):
        machine = self.get_or_new_machine(machine_name)
        link = self.get_or_new_link(link_name)

        machine.add_interface(machine_iface_number, link)

    def assign_meta_to_machine(self, machine_name, meta_name, meta_value):
        machine = self.get_or_new_machine(machine_name)

        machine.add_meta(meta_name, meta_value)

    def check_integrity(self):
        for machine in self.machines:
            self.machines[machine].check()

    def get_or_new_machine(self, name):
        """
        :param name: The name of the machine
        :return: The desired machine.
        :rtype: Machine
        """
        if name not in self.machines:
            self.machines[name] = Machine(self, name)

        return self.machines[name]

    def get_or_new_link(self, name):
        """
        :param name: The name of the link.
        :return: The desired link
        :rtype: Link
        """
        if name not in self.links:
            self.links[name] = Link(self, name)

        return self.links[name]

    def __repr__(self):
        return "Lab(%s, %s, %s, %s)" % (self.path, self.folder_hash, self.machines, self.links)
