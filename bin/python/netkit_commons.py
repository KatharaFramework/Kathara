import ConfigParser
config = ConfigParser.ConfigParser()
import StringIO
from itertools import chain
import re
from sys import platform as _platform
import os
import utils as u

#TODO test escapes, "" and '' in .startup files

DEBUG = True
PRINT = False
IMAGE_NAME = 'netkit'
DOCKER_HUB_PREFIX = "netkit/"
LINUX_TERMINAL_TYPE = 'xterm'

FORCE_LAB = False

MAC_OS = "darwin"
WINDOWS = "win32"
LINUX = "linux"
LINUX2 = "linux2"

PLATFORM = LINUX

if _platform == MAC_OS:
    PLATFORM = MAC_OS
elif _platform == WINDOWS:
    PLATFORM = WINDOWS

DOCKER_BIN = 'docker'

if PLATFORM != WINDOWS:
    DOCKER_BIN = os.environ['NETKIT_HOME'] + '/wrapper/bin/netkit_dw'

SEPARATOR_WINDOWS = ' & '
BASH_SEPARATOR = ' ; '

if PLATFORM == WINDOWS:
    BASH_SEPARATOR = SEPARATOR_WINDOWS

def lab_parse(path):
    if FORCE_LAB and (not os.path.exists(os.path.join(path, 'lab.conf'))):
        return ({}, [], {}, {})

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
                links.append(value)
            except ValueError:
                pass
            keys.append(key)
        else:
            m_keys.append(key)

    # we only need unique links
    links = set(links)
    # sort the keys so that we keep the order of the interfaces
    keys.sort(key=u.natural_keys)

    # we then get a dictionary of machines ignoring interfaces that have missing positions (eg: 1,3,6 instead of 0,1,2)
    machines = {}
    options = {}
    for key in keys: 
        splitted = key.split('[')
        name = splitted[0]
        splitted = splitted[1].split(']')
        try:
            ifnumber = int(splitted[0])
            if not machines.get(name):
                machines[name] = []
            if len(machines[name]) == 0 or machines[name][len(machines[name])-1][1] == ifnumber - 1:
                machines[name].append((config.get('dummysection', key), ifnumber))
        except ValueError:
            option = splitted[0]
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
    
    if DEBUG: print (machines, options, metadata)

    return machines, links, options, metadata


def create_commands(machines, links, options, metadata, path, execbash=False):
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
    for link in links:
        create_network_commands.append(create_network_template + prefix + link)
        lab_links_text += prefix + link + ' '

    # writing the network list in the temp file
    if not execbash:
        if not PRINT: u.write_temp(lab_links_text, u.generate_urlsafe_hash(path) + '_links')
    
    # generating commands for running the containers, copying the config folder and executing the terminals connected to the containers
    create_machine_template = docker + ' run -tid --privileged=true --name ' + prefix + '{machine_name} --hostname={machine_name} --network=' + prefix + '{first_link} {image_name}'
    # we could use -ti -a stdin -a stdout and then /bin/bash -c "commands;bash", 
    # but that woult execute commands like ifconfig BEFORE all the networks are linked
    create_machine_commands = []

    create_connection_template = docker + ' network connect ' + prefix + '{link} ' + prefix + '{machine_name}'
    create_connection_commands = []

    copy_folder_template = docker + ' cp "' + path + '{machine_name}/etc" ' + prefix + '{machine_name}:/'
    copy_folder_commands = []

    exec_template = docker + ' exec {params} -ti --privileged=true ' + prefix + '{machine_name} {command}'
    exec_commands = []
    startup_commands = []

    count = 0

    for machine_name, interfaces in machines.items():
        this_image = IMAGE_NAME

        # Parsing options from lab.conf
        machine_option_string = " "
        if options.get(machine_name):
            for opt, val in options[machine_name]:
                if opt=='mem' or opt=='M': 
                    machine_option_string+='--memory="'+ val +'" '
                if opt=='image' or opt=='i' or opt=='model-fs' or opt=='m' or opt=='f' or opt=='filesystem': 
                    this_image = DOCKER_HUB_PREFIX + val
                if opt=='eth': 
                    app = val.split(":")
                    create_network_commands.append(create_network_template + prefix + app[1])
                    repls = ('{link}', app[1]), ('{machine_name}', machine_name)
                    create_connection_commands.append(u.replace_multiple_items(repls, create_connection_template))
                    if not PRINT: u.write_temp(" " + prefix + app[1], u.generate_urlsafe_hash(path) + '_links')
                if opt=='e' or opt=='exec':
                    repls = ('{machine_name}', machine_name), ('{command}', 'bash -c "' + val.strip().replace('\\', '\\\\').replace('"', '\\\\"').replace("'", "\\\\'") + '"'), ('{params}', '-d')
                    startup_commands.append(u.replace_multiple_items(repls, exec_template))

        repls = ('{machine_name}', machine_name), ('{number}', str(count)), ('{first_link}', interfaces[0][0]), ('{image_name}', this_image)
        create_machine_commands.append(u.replace_multiple_items(repls, create_machine_template) + machine_option_string)
        count += 1
        for link,_ in interfaces[1:]:
            repls = ('{link}', link), ('{machine_name}', machine_name)
            create_connection_commands.append(u.replace_multiple_items(repls, create_connection_template))
        repls = ('{machine_name}', machine_name), ('{machine_name}', machine_name)
        copy_folder_commands.append(u.replace_multiple_items(repls, copy_folder_template))
        if PLATFORM == WINDOWS:
            repls = ('{machine_name}', machine_name), ('{command}', 'bash -c "echo -ne \'\033]0;' + machine_name + '\007\'; bash"'), ('{params}', '-e TERM=vt100')
        else:
            repls = ('{machine_name}', machine_name), ('{command}', 'bash'), ('{params}', '-e TERM=vt100')
        exec_commands.append(u.replace_multiple_items(repls, exec_template))
        lab_machines_text += prefix + machine_name + ' '

    # writing the container list in the temp file
    if not execbash:
        if not PRINT: u.write_temp(lab_machines_text, u.generate_urlsafe_hash(path) + '_machines')
        
    # for each machine we have to get the machine.startup file and insert every non empty line as a string inside an array of exec commands. We also replace escapes and quotes
    for machine_name, _ in machines.items():
        startup_file = os.path.join(path, machine_name + '.startup')
        if os.path.exists(startup_file):
            f = open(startup_file, 'r')
            for line in f:
                if line.strip() and line not in ['\n', '\r\n']:
                    repls = ('{machine_name}', machine_name), ('{command}', 'bash -c "' + line.strip().replace('\\', '\\\\').replace('"', '\\\\"').replace("'", "\\\\'") + '"'), ('{params}', '-d')
                    startup_commands.append(u.replace_multiple_items(repls, exec_template))
            f.close()
    
    commands = create_network_commands + create_machine_commands + create_connection_commands + copy_folder_commands

    return commands, startup_commands, exec_commands
