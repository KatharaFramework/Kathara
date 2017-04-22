import argparse
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import utils as u
import os
import sys

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')
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
    help='Print commands used to start the containers (containers are not started).'
)
parser.add_argument("--execbash", required=False, action="store_true", help=argparse.SUPPRESS)

args = parser.parse_args()

# applying parameter options (1/3)
if args.xterm and (" " not in args.xterm):
    nc.LINUX_TERMINAL_TYPE = args.xterm.replace('"', '').replace("'", '')

if args.force_lab: 
    nc.FORCE_LAB = True

if args.print_only:
    cr.PRINT = True

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
(machines, links, options, metadata) = nc.lab_parse(lab_path)

# applying parameter options (2/3)
# adding additional_options to options
for machine_name, _ in options.items():
    options[machine_name] = options[machine_name] + additional_options

# get command lists
(commands, startup_commands, exec_commands) = nc.create_commands(machines, links, options, metadata, lab_path, args.execbash)

# create lab
if not args.execbash:
    # removing \r from DOS/MAC files before docker cp
    for machine in machines:
        machine_path = os.path.join(lab_path, machine)
        fc.win2linux_all_files_in_dir(machine_path)
        # checking if folder tree for the given machine contains etc/zebra and if so rename it as etc/quagga before copy
        # TODO add warning for user
        if os.path.isdir(os.path.join(machine_path, "etc/zebra")):
            try:
                os.rename(os.path.join(machine_path, "etc/zebra"), os.path.join(machine_path, "etc/quagga"))
            except:
                pass
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
    for exec_command, machine_name in zip(exec_commands, machines):
        if nc.PLATFORM == nc.WINDOWS:        
            if cr.PRINT: sys.stderr.write(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END + "\n")
            else: print(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
        else:   
            if cr.PRINT: sys.stderr.write(machine_name + ";" + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END + "\n")
            else: print(machine_name + ";" + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)

# applying parameter options (3/3)
if args.list:
    print('"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')