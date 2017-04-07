import configparser
config = configparser.ConfigParser()
from itertools import chain
import re
from sys import platform as _platform
import subprocess
import os
import base64
import hashlib

#TODO machine names do not have to contain spaces, as well as link names
#TODO check for escapes, "" and '' in .startup files

DEBUG = True
IMAGE_NAME = 'netkit'
LINUX_TERMINAL_TYPE = 'xterm'
PATH_TO_TEST_LAB = '../../test/shared/MARACAS_lab/'

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
    DOCKER_BIN = 'sudo docker'

SEPARATOR_WINDOWS = ' & '
BASH_SEPARATOR = ' ; '

if PLATFORM == WINDOWS:
    BASH_SEPARATOR = SEPARATOR_WINDOWS

# helper functions for natural sorting
def atoi(text):
    return int(text) if text.isdigit() else text
def natural_keys(text):
    return [ atoi(c) for c in re.split('(\d+)', text) ]

def run_command_detatched(cmd_line):
    p = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0]
    return out

def replace_multiple_items(repls, string):
        return reduce(lambda a, kv: a.replace(*kv), repls, string)

def write_temp(text, filename):
    out_file = open(os.path.join(os.environ["NETKIT_HOME"], "temp/" + filename),"w+")
    out_file.write(text)
    out_file.close()

def generate_urlsafe_hash(string):
    return base64.urlsafe_b64encode(hashlib.md5(string).digest())[:-2]

def lab_parse(path = PATH_TO_TEST_LAB):
    # reads lab.conf
    with open(path + 'lab.conf') as stream:
        # adds a section to mimic a .ini file
        stream = chain(("[dummysection]",), stream)
        config.read_file(stream)

    # gets 2 list of keys, one for machines and the other for the metadata
    # we also need a unique list of links
    keys = []
    m_keys = []
    links = []
    for key in config['dummysection']: 
        if DEBUG: print(key, config['dummysection'][key])
        if '[' in key and ']' in key:
            splitted = key.split('[')[1].split(']')
            try:
                ifnumber = int(splitted[0])
                keys.append(key)
                links.append(config['dummysection'][key])
            except ValueError:
                m_keys.append(key)
        else:
            m_keys.append(key)

    # we only need unique links
    links = set(links)
    # sort the keys so that we keep the order of the interfaces
    keys.sort(key=natural_keys)

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
                machines[name].append((config['dummysection'][key], ifnumber))
        except ValueError:
            option = splitted[0]
            if not options.get(name):
                options[name] = []
                options[name].append((option, config['dummysection'][key]))
    # same with metadata
    metadata = {}
    for m_key in m_keys:
        if config['dummysection'][m_key].startswith('"') and config['dummysection'][m_key].endswith('"'):
            config['dummysection'][m_key] = config['dummysection'][m_key][1:-1]
        metadata[m_key] = config['dummysection'][m_key]
    
    if DEBUG: print (machines, options, metadata)

    return machines, links, options, metadata


def create_commands(machines, links, options, metadata, path = PATH_TO_TEST_LAB):
    docker = DOCKER_BIN

    if PLATFORM != WINDOWS:
        prefix = 'netkit_' + str(os.getuid()) + '_'
    else:
        prefix = 'netkit_nt_'

    lab_links_text = ''
    lab_machines_text = ''
        
    create_network_template = docker + ' network create '
    create_network_commands = []
    for link in links:
        create_network_commands.append(create_network_template + prefix + link)
        lab_links_text += prefix + link + ' '

    write_temp(lab_links_text, generate_urlsafe_hash(path) + '_links')
    
    create_machine_template = docker + ' run -tid --privileged=true --name ' + prefix + '{machine_name} --hostname={machine_name} --network=' + prefix + '{first_link} {image_name}'
    # we could use -ti -a stdin -a stdout and then /bin/bash -c "commands;bash", 
    # but that woult execute commands like ifconfig BEFORE all the networks are linked
    create_machine_commands = []

    create_connection_template = docker + ' network connect ' + prefix + '{link} ' + prefix + '{machine_name}'
    create_connection_commands = []

    copy_folder_template = docker + ' cp ' + path + '{machine_name}/etc ' + prefix + '{machine_name}:/'
    copy_folder_commands = []

    exec_template = docker + ' exec {params} -ti --privileged=true ' + prefix + '{machine_name} {command}'
    exec_commands = []

    count = 0

    for machine_name, interfaces in machines.items():
        repls = ('{machine_name}', machine_name), ('{number}', str(count)), ('{first_link}', interfaces[0][0]), ('{image_name}', IMAGE_NAME)
        create_machine_commands.append(replace_multiple_items(repls, create_machine_template))
        count += 1
        for link,_ in interfaces[1:]:
            repls = ('{link}', link), ('{machine_name}', machine_name)
            create_connection_commands.append(replace_multiple_items(repls, create_connection_template))
        repls = ('{machine_name}', machine_name), ('{machine_name}', machine_name)
        copy_folder_commands.append(replace_multiple_items(repls, copy_folder_template))
        if PLATFORM == WINDOWS:
            repls = ('{machine_name}', machine_name), ('{command}', 'bash -c "echo -ne \'\033]0;' + machine_name + '\007\'; bash"'), ('{params}', '-e TERM=debian')
        else:
            repls = ('{machine_name}', machine_name), ('{command}', 'bash -c "echo -ne \\\\"\\\\033]0;' + machine_name + '\\\\007\\\\"; bash"'), ('{params}', '-e TERM=debian')
        exec_commands.append(replace_multiple_items(repls, exec_template))
        lab_machines_text += prefix + machine_name + ' '

    write_temp(lab_machines_text, generate_urlsafe_hash(path) + '_machines')
        
    # for each machine we have to get the machine.startup file and insert every non empty line as a string inside an array
    startup_commands = []
    for machine_name, _ in machines.items():
        f = open(path + machine_name + '.startup', 'r')
        for line in f:
            if line.strip() and line not in ['\n', '\r\n']:
                repls = ('{machine_name}', machine_name), ('{command}', 'bash -c "' + line.strip().replace(r'\r\n', '\n') + '"'), ('{params}', '-d')
                startup_commands.append(replace_multiple_items(repls, exec_template))
        f.close()
    
    commands = create_network_commands + create_machine_commands + create_connection_commands + copy_folder_commands

    return commands, startup_commands, exec_commands
