import collections
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from distutils.util import strtobool
from glob import glob

from .. import utils
from ..exceptions import NonSequentialMachineInterfaceError, MachineOptionError
from ..setting.Setting import Setting


class Machine(object):
    __slots__ = ['lab', 'name', 'interfaces', 'meta', 'startup_commands', 'api_object', 'capabilities',
                 'startup_path', 'shutdown_path', 'folder']

    def __init__(self, lab, name):
        self.lab = lab
        self.name = name

        self.interfaces = {}

        self.meta = {'sysctls': {}, 'bridged': False, 'ports': {}}

        self.startup_commands = []

        self.api_object = None

        self.capabilities = ["NET_ADMIN", "NET_RAW", "NET_BROADCAST", "NET_BIND_SERVICE", "SYS_ADMIN"]

        startup_file = os.path.join(lab.path, '%s.startup' % self.name)
        self.startup_path = startup_file if os.path.exists(startup_file) else None

        shutdown_file = os.path.join(lab.path, '%s.shutdown' % self.name)
        self.shutdown_path = shutdown_file if os.path.exists(shutdown_file) else None

        machine_folder = os.path.join(lab.path, '%s' % self.name)
        self.folder = machine_folder if os.path.isdir(machine_folder) else None

    def add_interface(self, number, link):
        if number in self.interfaces:
            raise Exception("Interface %d already set on device `%s`." % (number, self.name))

        self.interfaces[number] = link

    def add_meta(self, name, value):
        if name == "exec":
            self.startup_commands.append(value)
            return

        if name == "bridged":
            self.meta[name] = bool(strtobool(str(value)))
            return

        if name == "sysctl":
            # Check for valid kv-pair
            if '=' in value:
                (key, val) = value.split('=')
                key = key.strip()
                val = val.strip()
                # Only allow `net.` namespace
                if key.startswith('net.'):
                    # Convert to int if possible
                    self.meta['sysctls'][key] = int(val) if val.isdigit() else val
                else:
                    raise MachineOptionError(
                        "Invalid sysctl value (`%s`) on `%s`, only `net.` namespace is allowed." % (value, self.name)
                    )
            else:
                raise MachineOptionError("Invalid sysctl value (`%s`) on `%s`, missing `=`." % (value, self.name))
            return

        if name == "port":
            if '/' in value:
                (ports, protocol) = value.split('/')
            else:
                (ports, protocol) = value, 'tcp'

            if ':' not in ports:
                host_port, guest_port = 3000, ports
            else:
                (host_port, guest_port) = ports.split(':')

            protocol = protocol.lower()
            if protocol not in ['tcp', 'udp', 'sctp']:
                raise MachineOptionError("Port protocol value not valid on `%s`." % self.name)

            try:
                self.meta['ports'][(int(host_port), protocol)] = int(guest_port)
            except ValueError:
                raise MachineOptionError("Port value not valid on `%s`." % self.name)
            return

        self.meta[name] = value

    def check(self):
        """
        Sorts the dictionary of interfaces ignoring the missing positions
        """
        sorted_interfaces = sorted(self.interfaces.items(), key=lambda kv: kv[0])

        logging.debug("`%s` interfaces are %s." % (self.name, sorted_interfaces))

        for i in range(1, len(sorted_interfaces)):
            if sorted_interfaces[i - 1][0] != sorted_interfaces[i][0] - 1:
                # If a number is non sequential, raise the exception.
                raise NonSequentialMachineInterfaceError("Interface %d missing on device %s." % (i, self.name))

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
                    if utils.is_excluded_file(file):
                        continue

                    # Removes the last element of the path
                    # (because it's the machine folder name and it should be included in the tar archive)
                    lab_path, machine_folder = os.path.split(self.folder)
                    (tarinfo, content) = utils.pack_file_for_tar(file,
                                                                 arcname="hostlab/%s" % os.path.relpath(file, lab_path)
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
        logging.debug("Opening terminal for device %s.", self.name)

        executable_path = utils.get_executable_path(sys.argv[0])

        if not executable_path:
            raise Exception("Unable to find Kathara.")

        connect_command = "%s connect -l %s" % (executable_path, self.name)
        terminal = terminal_name if terminal_name else Setting.get_instance().terminal

        logging.debug("Terminal will open in directory %s." % self.lab.path)

        def unix_connect():
            if terminal == "TMUX":
                from ..trdparty.libtmux.tmux import TMUX

                logging.debug("Attaching `%s` to TMUX session `%s` with command `%s`" % (self.name, self.lab.name,
                                                                                         connect_command))

                TMUX.get_instance().add_window(self.lab.name, self.name, connect_command, cwd=self.lab.path)
            else:
                logging.debug("Opening Linux terminal with command: %s." % connect_command)

                # Command should be passed as an array
                # https://stackoverflow.com/questions/9935151/popen-error-errno-2-no-such-file-or-directory/9935511
                subprocess.Popen([terminal, "-e", connect_command],
                                 cwd=self.lab.path,
                                 start_new_session=True
                                 )

        def windows_connect():
            complete_win_command = "& %s" % connect_command
            logging.debug("Opening Windows terminal with command: %s." % complete_win_command)
            subprocess.Popen(["powershell.exe",
                              '-Command',
                              complete_win_command
                              ],
                             creationflags=subprocess.CREATE_NEW_CONSOLE,
                             cwd=self.lab.path
                             )

        def osx_connect():
            complete_osx_command = "cd \"%s\" && clear && %s && exit" % (self.lab.path, connect_command)

            if terminal == "TMUX":
                from ..trdparty.libtmux.tmux import TMUX

                logging.debug("Attaching `%s` to TMUX session `%s` with command `%s`" % (self.name, self.lab.name,
                                                                                         complete_osx_command))

                TMUX.get_instance().add_window(self.lab.name, self.name, complete_osx_command, cwd=self.lab.path)
            else:
                import appscript
                logging.debug("Opening OSX terminal with command: %s." % complete_osx_command)
                terminal_app = appscript.app(terminal)
                if terminal == 'iTerm':
                    window = terminal_app.create_window_with_default_profile()
                    window.current_session.write(text=complete_osx_command)
                elif terminal == 'Terminal':
                    terminal_app.do_script(complete_osx_command)

        utils.exec_by_platform(unix_connect, windows_connect, osx_connect)

    def get_image(self):
        """
        Docker image, if defined in options or machine meta. If not use default one.
        :return: The Docker image to be used
        """
        return self.lab.general_options["image"] if "image" in self.lab.general_options else \
                self.meta["image"] if "image" in self.meta else Setting.get_instance().image

    def get_mem(self):
        """
        Memory limit, if defined in options. If not use the value from machine meta.
        :return: The memory limit of the image.
        """
        memory = self.lab.general_options["mem"] if "mem" in self.lab.general_options else \
            self.meta["mem"] if "mem" in self.meta else None

        if memory:
            unit = memory[-1].lower()
            if unit not in ["b", "k", "m", "g"]:
                try:
                    return "%sm" % int(memory)
                except ValueError:
                    raise MachineOptionError("Memory value not valid on `%s`." % self.name)

            try:
                return "%s%s" % (int(memory[:-1]), unit)
            except ValueError:
                raise MachineOptionError("Memory value not valid on `%s`." % self.name)

        return memory

    def get_cpu(self, multiplier=1):
        """
        CPU limit, multiplied by a specific multiplier.
        User should pass a float value ranging from 0 to max user CPUs.
        It is took from options, or machine meta.
        :return:
        """
        if "cpus" in self.lab.general_options:
            try:
                return int(float(self.lab.general_options["cpus"]) * multiplier)
            except ValueError:
                raise MachineOptionError("CPU value not valid on `%s`." % self.name)
        elif "cpus" in self.meta:
            try:
                return int(float(self.meta["cpus"]) * multiplier)
            except ValueError:
                raise MachineOptionError("CPU value not valid on `%s`." % self.name)

        return None

    def get_ports(self):
        if self.meta['ports']:
            return self.meta['ports']

        return None

    def get_num_terms(self):
        num_terms = 1

        if "num_terms" in self.lab.general_options:
            num_terms = self.lab.general_options['num_terms']
        elif 'num_terms' in self.meta:
            num_terms = self.meta['num_terms']

        try:
            num_terms = int(num_terms)

            if num_terms < 0:
                raise MachineOptionError("Terminals Number value on `%s` must be a positive value or zero." % self.name)
        except ValueError:
            raise MachineOptionError("Terminals Number value not valid on `%s`." % self.name)

        return num_terms

    def is_ipv6_enabled(self):
        try:
            return bool(strtobool(self.lab.general_options["ipv6"])) if "ipv6" in self.lab.general_options else \
                    bool(strtobool(self.meta["ipv6"])) if "ipv6" in self.meta else Setting.get_instance().enable_ipv6
        except ValueError:
            raise MachineOptionError("IPv6 value not valid on `%s`." % self.name)

    def __repr__(self):
        return "Machine(%s, %s, %s)" % (self.name, self.interfaces, self.meta)

    def add_meta_from_args(self, args):
        if args['eths']:
            for eth in args['eths']:
                try:
                    (iface_number, link_name) = eth.split(":")
                    self.lab.connect_machine_to_link(self.name, int(iface_number), link_name)
                except ValueError:
                    raise Exception("Interface number in `--eth %s` is not a number." % eth)

        if args['exec_commands']:
            for command in args['exec_commands']:
                self.add_meta("exec", command)

        if args['mem']:
            self.add_meta("mem", args['mem'])

        if args['cpus']:
            self.add_meta("cpus", args['cpus'])

        if args['image']:
            self.add_meta("image", args['image'])

        if args['bridged']:
            self.add_meta("bridged", True)

        if args['ports']:
            for port in args['ports']:
                self.add_meta("port", port)

        if args['num_terms']:
            self.add_meta('num_terms', args['num_terms'])

        if args['sysctls']:
            for sysctl in args['sysctls']:
                self.add_meta("sysctl", sysctl)