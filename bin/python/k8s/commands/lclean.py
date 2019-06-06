import argparse
import os
import shutil
import sys

from k8s import lab_deployer

def commandline_arg(bytestring):
    try:
        unicode_string = bytestring.decode(sys.getfilesystemencoding())
        return unicode_string
    except AttributeError:
        return bytestring

parser = argparse.ArgumentParser(description='Clean a Netkit Lab deployment on Kubernetes cluster.')
parser.add_argument('path', type=commandline_arg)
parser.add_argument(
    '-d', '--directory',
    required=False,
    help='Specify the folder containing the lab.'
)

args, unknown = parser.parse_known_args()

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
for machine_name, _ in options.items():
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
                if cr.PRINT:
                    sys.stderr.write(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END + "\n")
                else:
                    print(COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
            else:
                if cr.PRINT:
                    print(nc.LINUX_TERMINAL_TYPE + title_option + '"' + machine_name + '" -e "' + COMMAND_LAUNCHER +
                          exec_command + COMMAND_LAUNCHER_END + '"')
                else:
                    print(machine_name + ";" + COMMAND_LAUNCHER + exec_command + COMMAND_LAUNCHER_END)
else:
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
if args.list and (not cr.PRINT):
    if nc.PLATFORM == nc.WINDOWS:
        print('"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
    else:
        print("stats ;" + '"' + os.path.join(os.environ['NETKIT_HOME'], 'linfo') + '" -d "' + lab_path + '"')
