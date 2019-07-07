import argparse
import os
import re
import shutil
import sys
from sys import platform as _platform

import file_conversion as fc
import lstart_create as cr
import netkit_commons as nc
from k8s import lab_deployer
from netkit_commons import LINUX, LINUX2

DEBUG = nc.DEBUG
nc.DEBUG = False


# Don't do anything if this is imported as a module!
if __name__ != "__main__":
    exit()


def commandline_arg(bytestring):
    try:
        unicode_string = bytestring.decode(sys.getfilesystemencoding())
        return unicode_string
    except AttributeError:
        return bytestring

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path', type=commandline_arg)
parser.add_argument(
    "-n", "--noterminals", 
    required=False,
    action="store_true", 
    help='Start the lab without opening terminal windows.'
)
parser.add_argument(
    '-d', '--directory',
    required=False,
    help='Specify the folder containing the lab.'
)
parser.add_argument(
    '-F', '--force-lab',
    dest='force_lab',
    required=False,
    action='store_true', 
    help='Force the lab to start without a lab.conf or lab.dep file.'
)
parser.add_argument(
    '-f', '--fast',
    required=False,
    action='store_true', 
    help='DEPRECATED.'
)
parser.add_argument(
    '-l', '--list',
    required=False,
    action='store_true', 
    help='Show a list of running containers after the lab has been started.'
)
parser.add_argument(
    '-o', '--pass',
    dest='options',
    nargs='*',
    required=False, 
    help="Pass options to vstart. Options should be a list of double quoted strings, like '--pass \"mem=64m\" \"eth=0:A\"'."
)
parser.add_argument(
    '-p', '--parallel',
    required=False, 
    help='DEPRECATED.'
)
parser.add_argument(
    '-s', '--sequential',
    required=False,
    action='store_true', 
    help='DEPRECATED.'
)
parser.add_argument(
    '-w', '--wait',
    required=False,
    action='store_true',
    help='DEPRECATED.'
)
parser.add_argument(
    '--xterm',
    required=False,
    help='Set a different terminal emulator application (Unix only).'
)
parser.add_argument(
    '--print',
    dest="print_only",
    required=False,
    action='store_true',
    help='Print commands used to start the containers to stderr (containers are not started).'
)
parser.add_argument(
    '-c', '--counter',
    required=False,
    help='Start from a specific network counter (overrides whatever was previously initialized, using 0 will prompt the default behavior).'
)
parser.add_argument("--execbash", required=False, action="store_true", help=argparse.SUPPRESS)
parser.add_argument(
    '-k', '--k8s',
    required=False,
    action='store_true',
    help='Start the lab in Kubernetes mode. Lab will be deployed on the configured cluster and no terminals will open.'
)

args, unknown = parser.parse_known_args()

machine_name_args = list(filter(lambda x: not (x.startswith("--") or x.startswith("-")), unknown))

# applying parameter options (1/3)
title_option = " -T "
if args.xterm and (" " not in args.xterm):
    nc.LINUX_TERMINAL_TYPE = args.xterm.replace('"', '').replace("'", '')
    title_option = " --title="

FORCE_LAB = False
if args.force_lab: 
    FORCE_LAB = args.force_lab

network_counter = 0
if args.counter: 
    try: 
        network_counter = int(args.counter)
    except ValueError:
        pass

if args.print_only:
    cr.PRINT = True
    nc.PRINT = True

lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else \
           args.path.replace('"', '').replace("'", '')

# getting options from args.options and later append them to the options dictionary
additional_options = []
if args.options:
    for opt in args.options:
        app = opt.replace('"', '').replace("'", '').split("=")
        additional_options.append((app[0].strip(), app[1].strip()))

# get lab machines, options, links and metadata
(machines, links, options, metadata) = nc.lab_parse(lab_path, force=FORCE_LAB)

# applying parameter options (2/3)
# adding additional_options to options
# Loop through the machines
for machine_name, _ in machines.items():
    # Check if a machine already has options, if not create a list
    if machine_name not in options:
        options[machine_name] = []

    # Append additional_options to options
    options[machine_name] = options[machine_name] + additional_options

filtered_machines = machines

# filter machines based on machine_name_args (if at least one)
if len(machine_name_args) >= 1:
    filtered_machines = dict((k, machines[k]) for k, v in machines.items() if k in machine_name_args)

# if force-lab is set true and we have no machines from lab.conf we need to set machine names from args
if FORCE_LAB and (len(filtered_machines.items()) == 0):
    filtered_machines = dict((k, [('default', 0)]) for k in machine_name_args)
    links = ['default']

# some checks
if len(filtered_machines) < 1:
    sys.stderr.write("Please specify at least a machine.\n")
    sys.exit(1)

for _, interfaces in filtered_machines.items(): 
    if len(interfaces) < 1:
        sys.stderr.write("Please specify at least a link for every machine.\n")
        sys.exit(1)

external_commands = []
# check if exist external.conf file, if user have root permission for execute external.conf file and check platform
if os.path.exists(os.path.join(lab_path, 'external.conf')):
    if _platform == LINUX or _platform == LINUX2:
        if os.geteuid() == 0:
            collision_domains, external_interfaces = nc.external_parse(lab_path)
            # list of all interfaces
            list_interfaces = [iface for iface in os.listdir('/sys/class/net/') if
                               re.match('lo|wlx.*|docker0|veth.*', iface) is None]

            for collision_domain in collision_domains:
                # check collision domains specified in external.conf
                if collision_domain not in links:
                    sys.stderr.write(collision_domain + ' ' + 'is not a valid collision domain, please check your external.conf file.' + '\n')
                    sys.exit(1)

            for external_interface in external_interfaces:
                # check ethernet interface specified in external.conf
                if external_interface.__contains__("."):
                    prefix_interface = external_interface.split(".")[0]
                    if prefix_interface not in list_interfaces:
                        sys.stderr.write(external_interface + ' ' + 'is not a valid ethernet interface, please check your external.conf file.' + '\n')
                        sys.exit(1)
                else:
                    if external_interface not in list_interfaces:
                        sys.stderr.write(external_interface + ' ' + 'is not a valid ethernet interface, please check your external.conf file.' + '\n')
                        sys.exit(1)

            external_commands = nc.external_commands(lab_path, collision_domains, external_interfaces)
        else:
            sys.stderr.write("Please need root permission to execute external.conf file.\n")
            sys.exit(1)
    else:
        sys.stderr.write("Please only Linux operating system is supported.\n")
        sys.stderr.write("Your operating system is " + _platform + "." + "\n")
        sys.exit(1)

if not args.execbash:
    # removing \r from DOS/MAC files
    for machine in filtered_machines:
        machine_path = os.path.join(lab_path, machine)

        fc.win2linux_all_files_in_dir(machine_path)
        # checking if folder tree for the given machine contains etc/zebra (and we are not in print mode)
        # and if so rename it as etc/quagga before the copy to the container
        if (not nc.PRINT) and os.path.isdir(os.path.join(machine_path, "etc/zebra")):
            zebra_path = os.path.join(machine_path, "etc/zebra")
            quagga_path = os.path.join(machine_path, "etc/quagga")

            try:
                sys.stderr.write("Moving '" + zebra_path + "' to '" + quagga_path + "'\n")
                os.rename(zebra_path, quagga_path)
            except OSError:
                sys.stderr.write("ERROR: could not move '" + zebra_path + "' to '" + quagga_path + "'\n")

        if (not nc.PRINT) and os.path.isdir(os.path.join(machine_path, "var/www")) and \
                (not os.path.isdir(os.path.join(machine_path, "var/www/html"))):
            www_path = os.path.join(machine_path, "var/www")
            html_path = os.path.join(machine_path, "var/www/html")

            try:
                sys.stderr.write("Moving '" + www_path + "' to '" + html_path + "'\n")
                os.makedirs(html_path)

                for node in os.listdir(www_path):
                    if node != "html":
                        shutil.move(os.path.join(www_path, node), os.path.join(html_path, node))
            except OSError:
                sys.stderr.write("ERROR: could not move '" + www_path + "' to '" + html_path + "'\n")

if not args.k8s:
    # get command lists
    (commands, startup_commands, exec_commands) = nc.create_commands(
                                                    filtered_machines,
                                                    links,
                                                    options,
                                                    metadata,
                                                    lab_path,
                                                    args.execbash,
                                                    no_machines_tmp=(len(machine_name_args) >= 1),
                                                    network_counter=network_counter
                                                  )

    # create lab
    if not args.execbash:
        # running creation commands not verbosely
        cr.lab_create(commands, startup_commands, external_commands)
    else:
        cr.lab_create([], startup_commands, [])

    COMMAND_LAUNCHER = "bash -c '"
    COMMAND_LAUNCHER_END = "'"
    if nc.PLATFORM == nc.WINDOWS:
        COMMAND_LAUNCHER = 'start cmd /c "'
        COMMAND_LAUNCHER_END = '"'

    # print commands for terminal (exec bash commands to open terminals)
    if not args.noterminals:
        for exec_command, machine_name in zip(exec_commands, filtered_machines):
            if nc.PLATFORM == nc.WINDOWS:
                if cr.PRINT:
                    sys.stderr.write(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END + "\n")
                else:
                    print(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
            else:
                if cr.PRINT:
                    print(
                        nc.LINUX_TERMINAL_TYPE + title_option + '"' + machine_name + '" -e "' + COMMAND_LAUNCHER +
                        exec_command + COMMAND_LAUNCHER_END + '"'
                    )
                else:
                    print(machine_name + ";" + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
else:
    # Deploy parsed lab in Kubernetes cluster
    lab_deployer.deploy(
        filtered_machines,
        links,
        options,
        lab_path,
        network_counter=network_counter
    )

# applying parameter options (3/3)
if args.list and (not cr.PRINT):
    if not args.k8s:
        if nc.PLATFORM == nc.WINDOWS:
            print('"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
        else:
            print("stats ;" + '"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
    else:
        lab_deployer.get_lab_info(lab_path)
