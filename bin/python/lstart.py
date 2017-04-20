import argparse
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import utils as u
import os

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')
parser.add_argument("--execbash", action="store_true")
parser.add_argument("-n", "--noterminals", action="store_true")
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')

args = parser.parse_args()

lab_path = args.path.replace('"', '')
if args.directory:
    lab_path = args.directory.replace('"', '')

# get lab machines, options, links and metadata
(machines, links, options, metadata) = nc.lab_parse(lab_path)
# get command lists
(commands, startup_commands, exec_commands) = nc.create_commands(machines, links, options, metadata, lab_path)

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
            print(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
        else:        
            print(machine_name + ";" + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
