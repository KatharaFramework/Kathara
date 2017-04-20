import argparse
import shutil
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import utils as u
import sys
import re
import os

DEBUG = nc.DEBUG
nc.DEBUG = False

def conf_line_writer(eths):
    if (eths != None):
        interfaces = {}
        for eth in eths:
            match = re.search(r'([0-9]+):([A-Z]+)', eth)
            if match:
                interfaces[str(match.group(1))] = match.group(2)
        return interfaces

def startup_writer(machine_path, machine_name, commands):
    #creating {machine_name}.startup file
    if (commands != None):
        startupp = open(os.path.join(machine_path, machine_name + '.startup'), 'a+')
        for command in commands:
            startupp.write(command + "\n")

        startupp.close()

def create_lab(machine_path, machine_name, conf_lines):
    #creating lab.conf for single machine
    conf_line_template = '{machine_name}[{argument}]={value}\n'

    if not os.path.exists(machine_path):
        os.mkdir(machine_path)
    confp = open(os.path.join(machine_path, 'lab.conf'), 'w+')
    for key, value in conf_lines.items():
            repls = ('{machine_name}', machine_name), ('{argument}', str(key)), ('{value}', value)
            confp.write(u.replace_multiple_items(repls, conf_line_template))

    confp.close()

#parsing arguments
parser = argparse.ArgumentParser(description='Create and start a Netkit Machine.')
parser.add_argument('current_path')
parser.add_argument('machine_name')
parser.add_argument('--eth', dest='eths', nargs='*', help='Set a specific interface on a collision domain.')
parser.add_argument('-e', '--exec', dest='exe', nargs='*')

args = parser.parse_args()
machine_path = os.path.join(os.environ["NETKIT_HOME"], "temp/labs/" + args.machine_name)

#starting machine already started
if (os.path.exists(machine_path)):
    print machine_path
    sys.exit(0)

#starting machine already existing in current lab
if (os.path.exists(os.path.join(args.current_path, "lab.conf"))):
    (machines, links, options, metadata) = nc.lab_parse(args.current_path)
    if machines.get(args.machine_name) != None:
        #creating and updating interfaces in lab.conf
        conf_lines = {}
        if (args.eths != None):
            new_eths = conf_line_writer(args.eths)
            conf_lines = u.merge_two_dicts(u.couple_list_to_dict(machines[args.machine_name]), new_eths)
        else: conf_lines = u.couple_list_to_dict(machines[args.machine_name])

        create_lab(machine_path, args.machine_name, conf_lines)

        #copying and appending commands to startup file
        startup_path = os.path.join(args.current_path, args.machine_name + ".startup")
        if (os.path.exists(startup_path)):
            shutil.copy(startup_path, os.path.join(machine_path, args.machine_name + ".startup"))
        if (args.exe != None):
            startup_writer(machine_path, args.machine_name, args.exe)

        #copying machine folder
        folder_path = os.path.join(args.current_path, args.machine_name)
        if (os.path.exists(folder_path)):
            shutil.copytree(folder_path, os.path.join(machine_path, args.machine_name))

#starting new machine not existing in lab pointed by current directory
else:
    #creating and updating interfaces in lab.conf
    conf_lines = conf_line_writer(args.eths)
    create_lab(machine_path, args.machine_name, conf_lines)

    #copying and appending commands to startup file
    startup_writer(machine_path, args.machine_name, args.exe)

print machine_path
