import argparse
import shutil
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import utils as u
import sys
import re
import os
try:
    import pwd
except ImportError: #windows
    pass

DEBUG = nc.DEBUG
nc.DEBUG = False

if nc.PLATFORM != nc.WINDOWS:
        prefix = 'netkit_' + str(os.getuid()) + '_'
else:
    prefix = 'netkit_nt_'

#parsing arguments
parser = argparse.ArgumentParser(description='Create and start a Netkit Machine.')
parser.add_argument('current_path')
parser.add_argument('machine_name')
parser.add_argument('--eth', dest='eths', nargs='*', help='Set a specific interface on a collision domain.')
parser.add_argument('-e', '--exec', dest='exe', nargs='*', help='Execute a specific command in the container.')
parser.add_argument(
    '-k', '--kernel',
    required=False,
    help='DEPRECATED.'
)
parser.add_argument(
    '-M', '--mem',
    required=False,
    help='Limit the amount of RAM available for this container.'
)
parser.add_argument(
    '-i', '--image',
    required=False,
    help='Run this container with a specific Docker image.'
)
parser.add_argument(
    '-H', '--no-hosthome',
    required=False,
    action='store_true',
    help='DEPRECATED.'
)
parser.add_argument(
    '-m', '--model-fs',
    dest='model',
    required=False,
    help='The same of -i option.'
)
parser.add_argument(
    '-f', '--filesystem',
    required=False,
    help='The same of -i option.'
)
parser.add_argument(
    '-W', '--no-cow',
    required=False,
    action='store_true',
    help='DEPRECATED.'
)
parser.add_argument(
    '-D', '--hide-disk-file',
    required=False,
    action='store_true',
    help='DEPRECATED.'
)
parser.add_argument(
    '--con0',
    required=False,
    help='DEPRECATED.'
)
parser.add_argument(
    '--con1',
    required=False,
    help='DEPRECATED.'
)
parser.add_argument(
    '--xterm',
    required=False,
    help='Set a different terminal emulator application.'
)
parser.add_argument(
    '-l', '--hostlab',
    required=False,
    help='Set a path for a lab folder to search the specified machine.'
)
parser.add_argument(
    '-w', '--hostwd',
    required=False,
    help='DEPRECATED.'
)
parser.add_argument(
    '--append',
    required=False,
    help='DEPRECATED.'
)
parser.add_argument(
    '-F', '--foregroung',
    required=False,
    action='store_true',
    help='DEPRECATED.'
)
parser.add_argument(
    '-p', '--print',
    dest='print_only',
    required=False,
    action='store_true',
    help='Print commands used to start the container (it does not actually start it).'
)
parser.add_argument(
    '-q', '--quite',
    required=False,
    action='store_true',
    help='DEPRECATED.'
)

args, unknown = parser.parse_known_args()

if nc.PLATFORM == nc.WINDOWS:
    machine_path = os.path.join(os.environ["NETKIT_HOME"], "temp/labs/" + prefix + args.machine_name)
else:
    machine_path =  os.path.join(pwd.getpwuid(os.getuid()).pw_dir, "netkit_temp/labs/" + prefix + args.machine_name)

image = ""
if args.image:
    image = args.image
elif args.filesystem:
    image = args.filesystem
elif args.model:
    image = args.model

def eths_line_writer(eths):
    if (eths != None):
        interfaces = {}
        for eth in eths:
            match = re.search(r'([0-9]+):([A-Z]+)', eth)
            if match:
                interfaces[str(match.group(1))] = match.group(2)
        return interfaces

def conf_line_writer(conf_lines):
    if args.mem:
        conf_lines["mem"] = args.mem
    if image != "":
        conf_lines["image"] = image
    return conf_lines

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
    if conf_lines:
        for key, value in conf_lines.items():
                repls = ('{machine_name}', machine_name), ('{argument}', str(key)), ('{value}', value)
                confp.write(u.replace_multiple_items(repls, conf_line_template))
    confp.close()

def start_new_machine():
    #creating and updating interfaces in lab.conf
    conf_lines = eths_line_writer(args.eths)
    conf_lines = conf_line_writer(conf_lines)
    create_lab(machine_path, args.machine_name, conf_lines)

    #copying and appending commands to startup file
    startup_writer(machine_path, args.machine_name, args.exe)

def lstart_command_writer():
    command = '"' + machine_path + '"'
    if args.xterm:
        command += " --xterm=" + args.xterm
    if args.print_only:
        command += " --print"
    return command
    

#starting machine already started
if (os.path.exists(machine_path)): # TODO old check, has to be done with folder_hash and temp lab dir
    print lstart_command_writer()
    sys.exit(0)

#starting machine already existing in current lab
if args.hostlab: 
    if (os.path.exists(os.path.join(args.hostlab, "lab.conf"))):
        (machines, links, options, metadata) = nc.lab_parse(args.hostlab)
        if machines.get(args.machine_name) != None:
            #creating and updating interfaces in lab.conf
            conf_lines = {}
            if (args.eths != None):
                new_eths = eths_line_writer(args.eths)
                conf_lines = u.merge_two_dicts(u.couple_list_to_dict(machines[args.machine_name]), new_eths)
            else: conf_lines = u.couple_list_to_dict(machines[args.machine_name])
            conf_lines = conf_line_writer(conf_lines)

            create_lab(machine_path, args.machine_name, conf_lines)

            #copying and appending commands to startup file
            startup_path = os.path.join(args.hostlab, args.machine_name + ".startup")
            if (os.path.exists(startup_path)):
                shutil.copy(startup_path, os.path.join(machine_path, args.machine_name + ".startup"))
            if (args.exe != None):
                startup_writer(machine_path, args.machine_name, args.exe)

            #copying machine folder
            folder_path = os.path.join(args.hostlab, args.machine_name)
            if (os.path.exists(folder_path)):
                shutil.copytree(folder_path, os.path.join(machine_path, args.machine_name))
        else:
            start_new_machine()

#starting new machine not existing in lab pointed by current directory
else:
    start_new_machine()

print lstart_command_writer()
