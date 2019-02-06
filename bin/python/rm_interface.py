import os
import argparse
import sys
import command_utils as cu
import lstart_create as lc

parser = argparse.ArgumentParser()
parser.add_argument('path')
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')

args, unknown = parser.parse_known_args()

lab_path = args.path.replace('"', '').replace("'", '')
if args.directory:
    lab_path = args.directory.replace('"', '').replace("'", '')

#delete subinterface created with vlan_id
def remove_subinterface(path):
	delete_commands = []
	if os.path.exists(os.path.join(path, '.external_file.txt')):
		with open(os.path.join(path, '.external_file.txt'),'r') as external_file_temp:
			for line in external_file_temp:
				subinterface = line.split()[0]
				delete_commands.append('sudo ip link set dev ' + subinterface + ' ' + 'down')
				delete_commands.append('sudo ip link delete ' + subinterface)
		os.remove('.external_file.txt')
	return delete_commands

delete_commands = remove_subinterface(lab_path)
lc.external_create(delete_commands)
