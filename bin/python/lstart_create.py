import command_utils as cu
import netkit_commons as nc
import sys

DEBUG = nc.DEBUG
nc.DEBUG = False

PRINT = False

def lab_create(commands, startup_commands, external_commands):
    lab_create_command_string = ''
    for command in commands:
        lab_create_command_string += command + nc.BASH_SEPARATOR
    lab_create_command_string = lab_create_command_string[:len(lab_create_command_string)-2]
    if PRINT: 
        if nc.PLATFORM == nc.WINDOWS: sys.stderr.write(lab_create_command_string)
        else: print(lab_create_command_string)
    else:
        cu.run_command_detatched(lab_create_command_string)
        external_create(external_commands)

    for startup_command in startup_commands:
        if PRINT: 
            if nc.PLATFORM == nc.WINDOWS: sys.stderr.write(startup_command + "\n")
            else: print(startup_command)
        else: cu.run_command_detatched(startup_command)

#define a method for create external_commands
def external_create(external_commands):
    external_create_command_string = ''
    for command in external_commands:
        external_create_command_string += command + nc.BASH_SEPARATOR
    external_create_command_string = external_create_command_string[:len(external_create_command_string)-2]
    if PRINT:
        print(external_create_command_string)
    else: cu.run_command_detatched(external_create_command_string)
