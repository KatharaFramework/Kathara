import os

import utils
from .Link import Link
from .Machine import Machine
from ..parser.DepParser import DepParser


class Lab(object):
    __slots__ = ['description', 'version', 'author', 'email', 'web',
                 'machines', 'links', 'net_counter', 'folder_hash', 'path',
                 'shared_startup_path', 'shared_shutdown_path', 'shared_folder']

    def __init__(self, path):
        self.path = path
        self.folder_hash = utils.generate_urlsafe_hash(path)

        shared_startup_file = os.path.join(self.path, 'shared.startup')
        self.shared_startup_path = shared_startup_file if os.path.exists(shared_startup_file) else None

        shared_shutdown_file = os.path.join(self.path, 'shared.shutdown')
        self.shared_shutdown_path = shared_shutdown_file if os.path.exists(shared_shutdown_file) else None

        self.shared_folder = os.path.join(self.path, 'shared')
        if not os.path.isdir(self.shared_folder):
            os.mkdir(self.shared_folder)

        self.description = None
        self.version = None
        self.author = None
        self.email = None
        self.web = None

        self.machines = {}
        self.links = {}

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

    def check_dependencies(self):
        dependencies = DepParser.parse(self.path)

        if dependencies:
            machine_items = self.machines.items()

            # TODO: Do something
            # OrderedDict(sorted(machines.items(), key=lambda t: dep_sort(t[0], dependency_list)))

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

    def __str__(self):
        lab_info = ""

        if self.description:
            lab_info += "Description: %s\n" % self.description

        if self.version:
            lab_info += "Version: %s\n" % self.version

        if self.author:
            lab_info += "Author(s): %s\n" % self.author

        if self.email:
            lab_info += "Email: %s\n" % self.email

        if self.web:
            lab_info += "Website: %s" % self.web

        return lab_info
