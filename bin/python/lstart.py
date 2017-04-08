import argparse
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import os

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')
parser.add_argument("--execbash", action="store_true")
parser.add_argument("-n", "--noterminals", action="store_true")

args = parser.parse_args()

# get lab machines, options, links and metadata
(machines, links, options, metadata) = nc.lab_parse(args.path)
# get command lists
(commands, startup_commands, exec_commands) = nc.create_commands(machines, links, options, metadata, args.path)

# create lab
if not args.execbash:
    # removing \r from DOS/MAC files before docker cp
    for machine in machines:
        fc.win2linux_all_files_in_dir(os.path.join(args.path))
    # running creation commands not verbosely
    cr.lab_create(commands, startup_commands)

COMMAND_LAUNCHER = "bash -c '"
COMMAND_LAUNCHER_END = "'"
if nc.PLATFORM == nc.WINDOWS:
    COMMAND_LAUNCHER = 'start cmd /c "'
    COMMAND_LAUNCHER_END = '"'

# print commands for terminal (exec bash commands to open terminals)
if not args.noterminals:
    for exec_command in exec_commands:
        print(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)