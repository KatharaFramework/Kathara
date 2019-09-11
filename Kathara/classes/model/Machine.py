import collections
import os
import shutil
import tarfile
import tempfile


class Machine(object):
    __slots__ = ['lab', 'name', 'startup_path', 'shutdown_path', 'folder',
                 'interfaces', 'bridge', 'meta', 'startup_commands']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name

        self.interfaces = {}
        self.bridge = None

        self.meta = {}

        self.startup_commands = []

        startup_file = os.path.join(lab.path, '%s.startup' % self.name)
        self.startup_path = startup_file if os.path.exists(startup_file) else None

        shutdown_file = os.path.join(lab.path, '%s.shutdown' % self.name)
        self.shutdown_path = shutdown_file if os.path.exists(shutdown_file) else None

        machine_folder = os.path.join(lab.path, '%s' % self.name)
        self.folder = machine_folder if os.path.isdir(machine_folder) else None

    def add_interface(self, number, link):
        if number in self.interfaces:
            raise Exception("Interface %d already set on machine `%s`." % (number, self.name))

        self.interfaces[number] = link

    def add_meta(self, name, value):
        if name == "exec":
            self.startup_commands.append(value)
            return

        if name == "bridged":
            self.bridge = self.lab.get_or_new_link("docker_bridge")
            return

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

    def pack_data(self):
        # Make a temp folder and create a tar.gz of the lab directory
        temp_path = tempfile.mkdtemp()

        is_empty = True

        with tarfile.open("%s/hostlab.tar.gz" % temp_path, "w:gz") as tar:
            if self.folder:
                tar.add(self.folder, arcname="hostlab/%s" % self.name)
                is_empty = False

            if self.startup_path:
                tar.add(self.startup_path, arcname="hostlab/%s.startup" % self.name)
                is_empty = False

            if self.shutdown_path:
                tar.add(self.shutdown_path, arcname="hostlab/%s.shutdown" % self.name)
                is_empty = False

            if self.lab.shared_startup_path:
                tar.add(self.lab.shared_startup_path, arcname="hostlab/shared.startup")
                is_empty = False

            if self.lab.shared_shutdown_path:
                tar.add(self.lab.shared_shutdown_path, arcname="hostlab/shared.shutdown")
                is_empty = False

        # If no machine files are found, don't deploy anything.
        if is_empty:
            return None

        # Read tar.gz content
        with open("%s/hostlab.tar.gz" % temp_path, "rb") as tar_file:
            tar_data = tar_file.read()

        # Delete temporary tar.gz
        shutil.rmtree(temp_path)

        return tar_data

    def __repr__(self):
        return "Machine(%s, %s, %s)" % (self.name, self.interfaces, self.meta)
