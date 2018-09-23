import ConfigParser
config = ConfigParser.ConfigParser()
import StringIO
from itertools import chain
import re
import sys
from sys import platform as _platform
import os
import utils as u
import depgen as dpg
from collections import OrderedDict

DEBUG = True
PRINT = False
IMAGE_NAME = 'netkit_base'
DOCKER_HUB_PREFIX = "kathara/"
LINUX_TERMINAL_TYPE = 'xterm'

MAC_OS = "darwin"
WINDOWS = "win32"
LINUX = "linux"
LINUX2 = "linux2"

PLATFORM = LINUX

if _platform == MAC_OS:
    PLATFORM = MAC_OS
elif _platform == WINDOWS:
    PLATFORM = WINDOWS

def read_config():
    tmp_config = ConfigParser.ConfigParser()
    ini = '[dummysection]\n' + open(os.path.join(os.environ['NETKIT_HOME'], '..', 'config'), 'r').read()
    ini_string = StringIO.StringIO(ini)
    tmp_config.readfp(ini_string)
    conf = {}
    for key, value in tmp_config.items('dummysection'): 
        conf[key] = value
    return conf

kat_config = read_config()

try: 
    DOCKER_BIN = kat_config['win_bin']
except:
    DOCKER_BIN = 'docker'

if PLATFORM != WINDOWS:
    try: 
        DOCKER_BIN = kat_config['unix_bin']
    except:
        DOCKER_BIN = os.environ['NETKIT_HOME'] + '/wrapper/bin/netkit_dw'

SEPARATOR_WINDOWS = ' & '
BASH_SEPARATOR = ' ; '

if PLATFORM == WINDOWS:
    BASH_SEPARATOR = SEPARATOR_WINDOWS


def dep_sort(item, dependency_list):
    try:
        return dependency_list.index(item) + 1
    except:
        return 0

def reorder_by_lab_dep(path, machines):
    if not os.path.exists(os.path.join(path, 'lab.dep')): 
        return machines
    # getting dependencies inside a data structure
    dependencies = {}
    conf = open(os.path.join(path, 'lab.dep'), 'r')
    for line in conf:
        if line.strip() and line.strip() not in ['\n', '\r\n']:
            app = line.split(":")
            app[1] = re.sub('\s+', ' ', app[1]).strip()
            dependencies[app[0].strip()] = app[1].split(' ') # dependencies[machine3] = [machine1, machine2]

    # building dependency set
    if dpg.has_loop(dependencies):
        sys.stderr.write("WARNING: loop in lab.dep, it will be ignored. \n")
        return machines

    dependency_list = dpg.flatten(dependencies)
    # reordering machines
    ordered_machines = OrderedDict(sorted(machines.items(), key=lambda t: dep_sort(t[0], dependency_list)))
    return ordered_machines

def lab_parse(path, force=False):
    if (not force) and (not os.path.exists(os.path.join(path, 'lab.conf'))):
        print ("No lab.conf in given directory\n")
        sys.exit(1)

    if force and (not os.path.exists(os.path.join(path, 'lab.conf'))):
        return ({}, [], {}, {}) # has to get names from last positional args

    # reads lab.conf
    ini_str = '[dummysection]\n' + open(os.path.join(path, 'lab.conf'), 'r').read()
    ini_fp = StringIO.StringIO(ini_str)
    config.readfp(ini_fp)

    # gets 2 list of keys, one for machines and the other for the metadata
    # we also need a unique list of links
    keys = []
    m_keys = []
    links = []
    for key, value in config.items('dummysection'): 
        if DEBUG: print(key, value)
        if '[' in key and ']' in key:
            splitted = key.split('[')[1].split(']')
            try:
                _ = int(splitted[0])
                links.append(value.strip().replace('"','').replace("'",''))
            except ValueError:
                pass
            keys.append(key.strip())
        else:
            m_keys.append(key.strip())

    # we only need unique links
    links = set(links)
    # sort the keys so that we keep the order of the interfaces
    keys.sort(key=u.natural_keys)

    # we then get a dictionary of machines ignoring interfaces that have missing positions (eg: 1,3,6 instead of 0,1,2)
    machines = {}
    options = {}
    for key in keys: 
        splitted = key.split('[')
        name = splitted[0].strip()
        splitted = splitted[1].split(']')
        try:
            ifnumber = int(splitted[0].strip())
            if not machines.get(name):
                machines[name] = []
            if len(machines[name]) == 0 or machines[name][len(machines[name])-1][1] == ifnumber - 1:
                machines[name].append((config.get('dummysection', key), ifnumber))
        except ValueError:
            option = splitted[0].strip()
            if not options.get(name):
                options[name] = []
            options[name].append((option, config.get('dummysection', key)))
    # same with metadata
    metadata = {}
    for m_key in m_keys:
        app = config.get('dummysection', m_key)
        if app.startswith('"') and app.endswith('"'):
            app = app[1:-1]
        metadata[m_key] = app
    
    machines = reorder_by_lab_dep(path, machines)
    
    if DEBUG: print (machines, options, metadata)
    return machines, links, options, metadata


def create_commands(machines, links, options, metadata, path, execbash=False, no_machines_tmp=False):
    docker = DOCKER_BIN

    # deciding machine and network prefix in order to avoid conflicts with other users and containers
    if PLATFORM != WINDOWS:
        prefix = 'netkit_' + str(os.getuid()) + '_'
    else:
        prefix = 'netkit_nt_'

    # generating network create command and network names separated by spaces for the temp file
    lab_links_text = ''
    lab_machines_text = ''
        
    create_network_template = docker + ' network create '
    create_network_commands = []

    base_path = os.path.join(os.environ['NETKIT_HOME'], 'temp')
    if PLATFORM != WINDOWS:
        base_path = os.path.join(os.environ['HOME'], 'netkit_temp')
    network_counter = 0
    if not os.path.exists(os.path.join(base_path,'last_network_counter.txt')):
        last_network_counter = open(os.path.join(base_path,'last_network_counter.txt'), 'w')
        last_network_counter.close()

    with open(os.path.join(base_path,'last_network_counter.txt'), 'r') as last_network_counter:
        try:
            network_counter = int(last_network_counter.readline())
        except:
            network_counter = 0
        for link in links:
            create_network_commands.append(create_network_template + prefix + link + " --subnet=172." + str(19+network_counter) + ".0.0/16 --gateway=172." + str(19+network_counter) + ".0.1")
            lab_links_text += prefix + link + ' '
            network_counter = (network_counter + 1) % 236
    with open(os.path.join(base_path,'last_network_counter.txt'), 'w') as last_network_counter:
        last_network_counter.write(str(network_counter))
    
    # writing the network list in the temp file
    if not execbash:
        if not PRINT: u.write_temp(lab_links_text, u.generate_urlsafe_hash(path) + '_links', PLATFORM, file_mode="w+")
    
    # generating commands for running the containers, copying the config folder and executing the terminals connected to the containers
    if PLATFORM != WINDOWS:
        create_machine_template = docker + ' run -tid --privileged=true --name ' + prefix + '{machine_name} --hostname={machine_name} --network=' + prefix + '{first_link} {machine_options} {image_name}'
    else: 
        create_machine_template = docker + ' run --volume="' + os.path.expanduser('~') +'":/hosthome -tid --privileged=true --name ' + prefix + '{machine_name} --hostname={machine_name} --network=' + prefix + '{first_link} {machine_options} {image_name}'
    # we could use -ti -a stdin -a stdout and then /bin/bash -c "commands;bash", 
    # but that woult execute commands like ifconfig BEFORE all the networks are linked
    create_machine_commands = []

    create_connection_template = docker + ' network connect ' + prefix + '{link} ' + prefix + '{machine_name}'
    create_bridge_connection_template = docker + ' network connect {link} ' + prefix + '{machine_name}'
    create_connection_commands = []
    create_bridge_connection_commands = []

    copy_folder_template = docker + ' cp "' + path + '{machine_name}/{folder_or_file}" ' + prefix + '{machine_name}:/{dest}'
    copy_folder_commands = []

    exec_template = docker + ' exec {params} -i --privileged=true ' + prefix + '{machine_name} {command}'
    exec_commands = []
    startup_commands = []

    count = 0

    for machine_name, interfaces in machines.items():
        this_image = DOCKER_HUB_PREFIX + IMAGE_NAME
        this_shell = 'bash'

        # copying the hostlab directory
        if not execbash:
            copy_folder_commands.append(docker + ' cp "' + path + '" ' + prefix + machine_name + ':/hostlab')

	#get the shell we run inside docker
	if options.get(machine_name):
            matching = [s for s in options[machine_name] if "shell" in s]
            if len(matching) > 0:
                this_shell = matching[0][1]

        # applying docker patch for /proc and icmp
        repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.all.rp_filter=0"'), ('{params}', '')
        startup_commands.insert(0, u.replace_multiple_items(repls, exec_template))
        repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.default.rp_filter=0"'), ('{params}', '')
        startup_commands.insert(1, u.replace_multiple_items(repls, exec_template))
        repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.lo.rp_filter=0"'), ('{params}', '')
        startup_commands.insert(2, u.replace_multiple_items(repls, exec_template))
        repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.eth0.rp_filter=0"'), ('{params}', '')
        startup_commands.insert(2, u.replace_multiple_items(repls, exec_template))

        # Parsing options from lab.conf
        machine_option_string = " "
        if options.get(machine_name):
            for opt, val in options[machine_name]:
                if opt=='mem' or opt=='M': 
                    machine_option_string+='--memory='+ val.upper() +' '
                if opt=='image' or opt=='i' or opt=='model-fs' or opt=='m' or opt=='f' or opt=='filesystem': 
                    this_image = DOCKER_HUB_PREFIX + val
                if opt=='eth': 
                    app = val.split(":")
                    create_network_commands.append(create_network_template + prefix + app[1])
                    repls = ('{link}', app[1]), ('{machine_name}', machine_name)
                    create_connection_commands.append(u.replace_multiple_items(repls, create_connection_template))
                    if not PRINT: u.write_temp(" " + prefix + app[1], u.generate_urlsafe_hash(path) + '_links', PLATFORM)
                    repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.eth'+str(app[0])+'.rp_filter=0"'), ('{params}', '')
                    startup_commands.insert(4, u.replace_multiple_items(repls, exec_template))
                if opt=='bridged': 
                    repls = ('{link}', "bridge"), ('{machine_name}', machine_name)
                    create_bridge_connection_commands.append(u.replace_multiple_items(repls, create_bridge_connection_template))
                if opt=='e' or opt=='exec':
                    repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "' + val.strip().replace('\\', r'\\').replace('"', r'\\"').replace("'", r"\\'") + '"'), ('{params}', '-d')
                    startup_commands.append(u.replace_multiple_items(repls, exec_template))
                if opt=='port': 
                    machine_option_string+='-p='+ val.upper() +':3000' + ' '
        repls = ('{machine_name}', machine_name), ('{number}', str(count)), ('{first_link}', interfaces[0][0]), ('{image_name}', this_image), ('{machine_options}', machine_option_string)
        create_machine_commands.append(u.replace_multiple_items(repls, create_machine_template))
        count += 1
        eth_cnt=1
        for link,_ in interfaces[1:]:
            repls = ('{link}', link), ('{machine_name}', machine_name)
            create_connection_commands.append(u.replace_multiple_items(repls, create_connection_template))
            repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "sysctl net.ipv4.conf.eth'+str(eth_cnt)+'.rp_filter=0"'), ('{params}', '')
            startup_commands.insert(4, u.replace_multiple_items(repls, exec_template))
            eth_cnt+=1
        # convoluted method to copy MACHINE_NAME/etc folder to the etc of the container
        if os.path.exists(os.path.join(path, machine_name)) and not execbash:
            for folder_or_file in os.listdir(os.path.join(path, machine_name)):
                if folder_or_file == 'etc': 
                    repls = ('{machine_name}', machine_name), ('{machine_name}', machine_name), ('{folder_or_file}', folder_or_file), ('{dest}', 'temp_etc')
                    repls2 = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "chmod -R 777 /temp_etc/*; cp -rfp /temp_etc/* /etc/; rm -rf /temp_etc; mkdir /var/log/zebra; chmod -R 777 /var/log/quagga; chmod -R 777 /var/log/zebra"'), ('{params}', '')
                    startup_commands.insert(0, u.replace_multiple_items(repls2, exec_template))
                else:
                    repls = ('{machine_name}', machine_name), ('{machine_name}', machine_name), ('{folder_or_file}', folder_or_file), ('{dest}', '')
                copy_folder_commands.append(u.replace_multiple_items(repls, copy_folder_template))
        if PLATFORM == WINDOWS:
            repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "echo -ne \'\033]0;' + machine_name + '\007\'; bash"'), ('{params}', '-t -e TERM=vt100')
        else:
            repls = ('{machine_name}', machine_name), ('{command}', this_shell), ('{params}', '-t -e TERM=vt100')
        exec_commands.append(u.replace_multiple_items(repls, exec_template))
        lab_machines_text += prefix + machine_name + ' '

    # writing the container list in the temp file
    if not no_machines_tmp:
        if not execbash:
            if not PRINT: u.write_temp(lab_machines_text, u.generate_urlsafe_hash(path) + '_machines', PLATFORM)


    # for each machine we have to get the machine.startup file and insert every non empty line as a string inside an array of exec commands. We also replace escapes and quotes
    for machine_name, _ in machines.items():
        startup_file = os.path.join(path, machine_name + '.startup')
        if os.path.exists(startup_file):
            f = open(startup_file, 'r')
            full_startup_command = ''
            for line in f:
                if line.strip() and line.strip() not in ['\n', '\r\n']:
                    full_startup_command += line.strip().replace('\\', r'\\').replace('"', r'\"').replace("'", r"\'") + ';'
            f.close()
            repls = ('{machine_name}', machine_name), ('{command}', this_shell + ' -c "' + full_startup_command + '"'), ('{params}', '-d')
            startup_commands.append(u.replace_multiple_items(repls, exec_template))
    
    commands = create_network_commands + create_machine_commands + create_connection_commands + create_bridge_connection_commands + copy_folder_commands

    return commands, startup_commands, exec_commands
