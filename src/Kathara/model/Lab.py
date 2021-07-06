import collections
import os
from itertools import chain

from .Link import Link
from .Machine import Machine
from .. import utils


class Lab(object):
    __slots__ = ['name', 'description', 'version', 'author', 'email', 'web',
                 'path', 'hash', 'machines', 'links', 'general_options', 'has_dependencies',
                 'shared_startup_path', 'shared_shutdown_path', 'shared_folder']

    def __init__(self, name, path=None):
        self.name = name
        self.description = None
        self.version = None
        self.author = None
        self.email = None
        self.web = None

        self.machines = {}
        self.links = {}

        self.general_options = {}

        self.has_dependencies = False

        self.path = path
        self.shared_startup_path = None
        self.shared_shutdown_path = None

        if self.path:
            self.path = path
            self.hash = utils.generate_urlsafe_hash(self.path)
            shared_startup_file = os.path.join(self.path, 'shared.startup')
            self.shared_startup_path = shared_startup_file if os.path.exists(shared_startup_file) else None

            shared_shutdown_file = os.path.join(self.path, 'shared.shutdown')
            self.shared_shutdown_path = shared_shutdown_file if os.path.exists(shared_shutdown_file) else None
        else:
            self.hash = utils.generate_urlsafe_hash(self.name)

        self.shared_folder = None

    def connect_machine_to_link(self, machine_name, link_name, machine_iface_number=None):
        machine = self.get_or_new_machine(machine_name)
        link = self.get_or_new_link(link_name)

        machine.add_interface(link, number=machine_iface_number)

    def assign_meta_to_machine(self, machine_name, meta_name, meta_value):
        machine = self.get_or_new_machine(machine_name)

        machine.add_meta(meta_name, meta_value)

    def attach_external_links(self, external_links):
        for (link_name, link_external_links) in external_links.items():
            if link_name not in self.links:
                raise Exception("Collision domain `%s` (declared in lab.ext) not found in lab "
                                "collision domains." % link_name)

            self.links[link_name].external += link_external_links

    def check_integrity(self):
        for machine in self.machines:
            self.machines[machine].check()

    def intersect_machines(self, selected_machines):
        """
        Intersect lab machines with selected machines, passed from command line.
        :param selected_machines: An array with selected machines names.
        """
        # Intersect selected machines names with self.machines keys
        selected_machines = set(self.machines.keys()) & set(selected_machines)
        # Apply filtering
        self.machines = {k: v for (k, v) in self.machines.items() if k in selected_machines}

        # Also updates lab links in order to avoid deploying unused ones.
        # Get only selected machines Link objects.
        selected_links = chain.from_iterable([machine.interfaces.values() for (_, machine) in self.machines.items()])
        # Get names of links (which are also the keys of self.links dict)
        selected_links = set([link.name for link in selected_links])
        # Apply filtering
        self.links = {k: v for (k, v) in self.links.items() if k in selected_links}

    def apply_dependencies(self, dependencies):
        if dependencies:
            def dep_sort(item):
                try:
                    return dependencies.index(item) + 1
                except ValueError:
                    return 0

            self.machines = collections.OrderedDict(sorted(self.machines.items(), key=lambda t: dep_sort(t[0])))
            self.has_dependencies = True

    def get_or_new_machine(self, name, **kwargs):
        """
        :param name: The name of the machine
        :return: The desired machine.
        :rtype: Machine
        """
        if name not in self.machines:
            self.machines[name] = Machine(self, name, **kwargs)

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

    def create_shared_folder(self):
        if not self.has_path():
            return
        try:
            self.shared_folder = os.path.join(self.path, 'shared')
            if not os.path.isdir(self.shared_folder):
                os.mkdir(self.shared_folder)
            elif os.path.islink(self.shared_folder):
                raise Exception("`shared` folder is a symlink, delete it.")
        except OSError:
            # Do not create shared folder if not permitted.
            return

    def has_path(self):
        return self.path is not None

    def add_option(self, name, value):
        if value is not None:
            self.general_options[name] = value

    def __repr__(self):
        return "Lab(%s, %s, %s, %s)" % (self.path, self.hash, self.machines, self.links)

    def __str__(self):
        lab_info = ""

        if self.name:
            lab_info += "Name: %s\n" % self.name

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
