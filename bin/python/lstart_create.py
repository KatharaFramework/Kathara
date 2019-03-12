import command_utils as cu
import netkit_commons as nc
import utils as u
import sys
import os

DEBUG = nc.DEBUG
nc.DEBUG = False

PRINT = False

def lab_create(commands, startup_commands):
    lab_create_command_string = ''
    for command in commands:
        if nc.PLATFORM == nc.WINDOWS: lab_create_command_string += "CALL " + command + "\n"
        else: lab_create_command_string += command + "\n"
    if PRINT: 
        if nc.PLATFORM == nc.WINDOWS: sys.stderr.write(lab_create_command_string + "\n")
        else: print(lab_create_command_string)
    else:
        if nc.PLATFORM == nc.WINDOWS: 
            u.write_temp("@ECHO OFF \n\n" + lab_create_command_string, "last_lab_creation.bat", mode=nc.PLATFORM, file_mode="w")
            cu.run_command_detatched('cd "' + u.get_temp_folder(mode=nc.PLATFORM) + '"' + nc.BASH_SEPARATOR + "last_lab_creation.bat")
        else: 
            u.write_temp("#!/bin/bash \n\n" + lab_create_command_string, "last_lab_creation.sh", mode=nc.PLATFORM, file_mode="w")
            os.chmod("my_script.sh", 0o755)
            cu.run_command_detatched('cd "' + u.get_temp_folder(mode=nc.PLATFORM) + '"' + nc.BASH_SEPARATOR + "last_lab_creation.sh")

    for startup_command in startup_commands:
        if PRINT: 
            if nc.PLATFORM == nc.WINDOWS: sys.stderr.write(startup_command + "\n")
            else: print(startup_command)
        else: cu.run_command_detatched(startup_command)
