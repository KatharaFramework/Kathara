import netkit_commons as nc
DEBUG = nc.DEBUG
nc.DEBUG = False

def lab_create(commands, startup_commands):
    lab_create_command_string = ''
    for command in commands:
        lab_create_command_string += command + nc.BASH_SEPARATOR
    lab_create_command_string = lab_create_command_string[:len(lab_create_command_string)-2]
    nc.run_command_detatched(lab_create_command_string)

    for startup_command in startup_commands:
        nc.run_command_detatched(startup_command)