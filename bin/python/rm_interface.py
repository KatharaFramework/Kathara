import os
import argparse
import sys
import lstart_create as lc
import utils as u
import pwd
from sys import platform as _platform
from netkit_commons import LINUX, LINUX2

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
	if (_platform == LINUX or _platform == LINUX2):
		if (os.geteuid() == 0):
			temp_path = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, "netkit_temp/")
			hash_path = str(u.generate_urlsafe_hash(path))
			if (os.path.exists(temp_path + hash_path + '_external_links')):
				if (os.stat(temp_path + hash_path + '_external_links').st_size != 0):
					with open(temp_path + hash_path + '_external_links', 'r') as external_file_temp:
						delete_commands.append('echo "\033[0;33mSubinterfaces will be deleted\033[0m"')
						for line in external_file_temp:
							subinterface = line.split()[0]
							delete_commands.append('sudo ip link set dev ' + subinterface + ' ' + 'down')
							delete_commands.append('sudo ip link delete ' + subinterface)
							delete_commands.append('echo ' + subinterface)

				os.remove(temp_path + hash_path + '_external_links')
		else:
			sys.stderr.write("\033[0;33mPlease you started the lab with external.conf file, need root permission to clean current lab.\033[0m" +"\n")
			sys.exit(1)

	return delete_commands

delete_commands = remove_subinterface(lab_path)
lc.external_create(delete_commands)
