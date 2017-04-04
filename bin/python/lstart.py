import argparse

# TODO get argument from current directory

import netkit_commons as nc 
import lstart_create as cr

DEBUG = nc.DEBUG
nc.DEBUG = False

# get lab machines, options, links and metadata
(machines, links, options, metadata) = nc.lab_parse()
# get command lists
(commands, startup_commands, exec_commands) = nc.create_commands(machines, links, options, metadata)

# create lab
cr.lab_create(commands, startup_commands)

# print commands for terminal
for exec_command in exec_commands:
    print("bash -c '" + exec_command + "'")
