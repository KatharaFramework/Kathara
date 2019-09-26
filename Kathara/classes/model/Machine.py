import collections
import os
import shutil
import subprocess
import tarfile
import tempfile
from glob import glob

import utils
from .Link import BRIDGE_LINK_NAME
from ..setting.Setting import Setting


class Machine(object):
    __slots__ = ['lab', 'name', 'startup_path', 'shutdown_path', 'folder',
                 'interfaces', 'bridge', 'meta', 'startup_commands', 'api_object']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name

        self.interfaces = {}
        self.bridge = None

        self.meta = {}

        self.startup_commands = []

        self.api_object = None

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
            self.bridge = self.lab.get_or_new_link(BRIDGE_LINK_NAME)
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
        """
        Pack machine data into a .tar.gz file and returns the tar content as a byte array.
        While packing files, it also applies the win2linux patch in order to remove UTF-8 BOM.
        """
        # Make a temp folder and create a tar.gz of the lab directory
        temp_path = tempfile.mkdtemp()

        is_empty = True

        with tarfile.open("%s/hostlab.tar.gz" % temp_path, "w:gz") as tar:
            if self.folder:
                machine_files = filter(os.path.isfile, glob("%s/**" % self.folder, recursive=True))

                for file in machine_files:
                    (tarinfo, content) = utils.pack_file_for_tar(file,
                                                                 arcname="hostlab/%s" % os.path.relpath(file,
                                                                                                        self.folder
                                                                                                        )
                                                                 )
                    tar.addfile(tarinfo, content)

                is_empty = False

            if self.startup_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.startup_path,
                                                             arcname="hostlab/%s.startup" % self.name
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

            if self.shutdown_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.shutdown_path,
                                                             arcname="hostlab/%s.shutdown" % self.name
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

            if self.lab.shared_startup_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.lab.shared_startup_path,
                                                             arcname="hostlab/shared.startup"
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

            if self.lab.shared_shutdown_path:
                (tarinfo, content) = utils.pack_file_for_tar(self.lab.shared_shutdown_path,
                                                             arcname="hostlab/shared.shutdown"
                                                             )
                tar.addfile(tarinfo, content)
                is_empty = False

        # If no machine files are found, return None.
        if is_empty:
            return None

        # Read tar.gz content
        with open("%s/hostlab.tar.gz" % temp_path, "rb") as tar_file:
            tar_data = tar_file.read()

        # Delete temporary tar.gz
        shutil.rmtree(temp_path)

        return tar_data

    def connect(self, terminal_name):
        # TODO: Change executable path

        connect_command = "/home/lollo/git/ookathara/Kathara/dist/kathara connect %s" % self.name
        terminal = terminal_name if terminal_name else Setting.get_instance().terminal

        def unix_connect():
            # Remember this https://stackoverflow.com/questions/9935151/popen-error-errno-2-no-such-file-or-directory/9935511
            subprocess.Popen([terminal, "-e", connect_command],
                             cwd=self.lab.path,
                             start_new_session=True
                             )

        def windows_connect():
            subprocess.Popen(["powershell.exe",
                              '-Command',
                              connect_command
                              ],
                             creationflags=subprocess.CREATE_NEW_CONSOLE,
                             cwd=self.lab.path
                             )

        def osx_connect():
            import appscript
            appscript.app('Terminal').do_script("cd " + self.lab.path + " && clear &&" + connect_command + " && exit")

        utils.exec_by_platform(unix_connect, windows_connect, osx_connect)

    def __repr__(self):
        return "Machine(%s, %s, %s)" % (self.name, self.interfaces, self.meta)
