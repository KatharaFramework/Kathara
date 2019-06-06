import os
import sys
import lstart_create as lc
import utils as u
import pwd
from sys import platform as _platform
from netkit_commons import LINUX, LINUX2
import re


#delete subinterface created with vlan_id
def lwipe_subinterface():
	delete_commands = []
	if (_platform == LINUX or _platform == LINUX2):
		temp_path = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, "netkit_temp/")
		list_external_files = [file for file in os.listdir(temp_path) if re.match('.*_external_links', file)]
		if len(list_external_files) != 0:
			sys.stderr.write("\033[0;33mSubinterfaces will be deleted\033[0m\n")
			for file in list_external_files:
				if (os.stat(temp_path + file).st_size != 0):
					with open(temp_path + file, 'r') as external_file_temp:
						for line in external_file_temp:
							subinterface = line.split()[0]
							delete_commands.append('sudo ip link set dev ' + subinterface + ' ' + 'down')
							delete_commands.append('sudo ip link delete ' + subinterface)
							delete_commands.append('echo ' + subinterface)
					os.remove(temp_path + file)
			lc.external_create(delete_commands)
				

lwipe_subinterface()
