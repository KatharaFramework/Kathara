import argparse
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import utils as u
import os
import sys
import shutil

DEBUG = nc.DEBUG
nc.DEBUG = False

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
    help='Specify the folder contining the lab.'
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
    help='Show a list of running container after the lab has been started.'
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
parser.add_argument("--execbash", required=False, action="store_true", help=argparse.SUPPRESS)

args, unknown = parser.parse_known_args()

machine_name_args = list([x for x in unknown if not (x.startswith("--") or x.startswith("-"))])

# applying parameter options (1/3)
title_option = " -T "
if args.xterm and (" " not in args.xterm):
    nc.LINUX_TERMINAL_TYPE = args.xterm.replace('"', '').replace("'", '')
    title_option = " --title="

FORCE_LAB=False
if args.force_lab: 
    FORCE_LAB = args.force_lab

if args.print_only:
    cr.PRINT = True
    nc.PRINT = True

lab_path = args.path.replace('"', '').replace("'", '')
if args.directory:
    lab_path = args.directory.replace('"', '').replace("'", '')

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
for machine_name, _ in list(options.items()):
    options[machine_name] = options[machine_name] + additional_options

filtered_machines = machines

# filter machines based on machine_name_args (if at least one)
if len(machine_name_args) >= 1:
    filtered_machines = dict((k, machines[k]) for k,v in list(machines.items()) if k in machine_name_args)

# if force-lab is set true and we have no machines from lab.conf we need to set machine names from args
if FORCE_LAB and (len(list(filtered_machines.items())) == 0):
    filtered_machines = dict((k, [('default', 0)]) for k in machine_name_args)
    links = ['default']

# some checks
if len(filtered_machines) < 1:
    sys.stderr.write("Please specify at least a machine.\n")
    sys.exit(1)
for _, interfaces in list(filtered_machines.items()): 
	if len(interfaces) < 1:
		sys.stderr.write("Please specify at least a link for every machine.\n")
		sys.exit(1)

# get command lists
(commands, startup_commands, exec_commands) = nc.create_commands(filtered_machines, links, options, metadata, lab_path, args.execbash, no_machines_tmp=(len(machine_name_args) >= 1))

# create lab
if not args.execbash:
    # removing \r from DOS/MAC files before docker cp
    for machine in filtered_machines:
        machine_path = os.path.join(lab_path, machine)
        fc.win2linux_all_files_in_dir(machine_path)
        # checking if folder tree for the given machine contains etc/zebra (and we are not in print mode) 
        # and if so rename it as etc/quagga before the copy to the container
        if os.path.isdir(os.path.join(machine_path, "etc/zebra")) and (not cr.PRINT):
            try:
                sys.stderr.write("Moving '" + os.path.join(machine_path, "etc/zebra") + "' to '" + os.path.join(machine_path, "etc/quagga") + "'\n")
                os.rename(os.path.join(machine_path, "etc/zebra"), os.path.join(machine_path, "etc/quagga"))
            except:
                sys.stderr.write("ERROR: could not move '" + os.path.join(machine_path, "etc/zebra") + "' to '" + os.path.join(machine_path, "etc/quagga") + "'\n")
        if os.path.isdir(os.path.join(machine_path, "var/www")) and (not os.path.isdir(os.path.join(machine_path, "var/www/html"))) and (not cr.PRINT):
            try:
                sys.stderr.write("Moving '" + os.path.join(machine_path, "var/www") + "' to '" + os.path.join(machine_path, "var/www/html") + "'\n")
                os.makedirs(os.path.join(machine_path, "var/www/html"))
                for node in os.listdir(os.path.join(machine_path, "var/www")):
                    if node != "html":
                        shutil.move(os.path.join(os.path.join(machine_path, "var/www"), node), os.path.join(os.path.join(machine_path, "var/www/html"), node))
            except:
                sys.stderr.write("ERROR: could not move '" + os.path.join(machine_path, "var/www") + "' to '" + os.path.join(machine_path, "var/www/html") + "'\n")
    # running creation commands not verbosely
    cr.lab_create(commands, startup_commands)
else:
    cr.lab_create([], startup_commands)

COMMAND_LAUNCHER = "bash -c '"
COMMAND_LAUNCHER_END = "'"
if nc.PLATFORM == nc.WINDOWS:
    COMMAND_LAUNCHER = 'start cmd /c "'
    COMMAND_LAUNCHER_END = '"'

# print commands for terminal (exec bash commands to open terminals)
if not args.noterminals:
    for exec_command, machine_name in zip(exec_commands, filtered_machines):
        if nc.PLATFORM == nc.WINDOWS:        
            if cr.PRINT: sys.stderr.write(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END + "\n")
            else: print(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
        else:
            if cr.PRINT: print(nc.LINUX_TERMINAL_TYPE + title_option + '"' + machine_name + '" -e "' + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END + '"')
            else: print(machine_name + ";" + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)

# applying parameter options (3/3)
if args.list and (not cr.PRINT):
    if nc.PLATFORM == nc.WINDOWS:
        print('"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
    else:
        print("stats ;" + '"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
