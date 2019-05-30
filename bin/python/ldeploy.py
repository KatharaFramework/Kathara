import argparse
import os
import shutil
import sys

import file_conversion as fc
import netkit_commons as nc
from k8s import lab_deployer

DEBUG = nc.DEBUG
nc.DEBUG = False


def commandline_arg(bytestring):
    try:
        unicode_string = bytestring.decode(sys.getfilesystemencoding())
        return unicode_string
    except AttributeError:
        return bytestring

parser = argparse.ArgumentParser(description='Deploy a Netkit Lab to the Kubernetes Cluster.')

parser.add_argument('path', type=commandline_arg)
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
    '-l', '--list',
    required=False,
    action='store_true',
    help='Show a list of running pods after the lab has been started.'
)
parser.add_argument(
    '-o', '--pass',
    dest='options',
    nargs='*',
    required=False,
    help="Pass options to vstart. Options should be a list of double quoted strings, like '--pass \"mem=64m\" \"eth=0:A\"'."
)
parser.add_argument(
    '--print',
    dest="print_only",
    required=False,
    action='store_true',
    help='Print network and pod definitions used to start the lab to stderr (pods are not deployed).'
)
parser.add_argument(
    '-c', '--counter',
    required=False,
    help='Start from a specific network counter (overrides whatever was previously initialized, using 0 will prompt the default behavior).'
)

args, unknown = parser.parse_known_args()

machine_name_args = list(filter(lambda x: not (x.startswith("--") or x.startswith("-")), unknown))

# applying parameter options (1/3)
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

# Deploy parsed lab in Kubernetes cluster
lab_deployer.deploy(
    filtered_machines,
    links,
    options,
    lab_path,
    no_machines_tmp=(len(machine_name_args) >= 1),
    network_counter=network_counter
)

# applying parameter options (3/3)
if args.list and (not nc.PRINT):
    if nc.PLATFORM == nc.WINDOWS:
        print('"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
    else:
        print("stats ;" + '"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
