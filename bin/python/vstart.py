import argparse
import netkit_commons as nc 
import file_conversion as fc
import lstart_create as cr
import utils as u
import re
import os

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser(description='Create and start a Netkit Machine.')
parser.add_argument('path')
parser.add_argument('machine_name')
parser.add_argument('eths', nargs='*')

args = parser.parse_args()

conf_line_template = '{machine_name}[{argument}]={value}\n'
create_machine_conf = []

for eth in args.eths:
    match = re.search(r'eth([0-9]+)=([A-Z]+)', eth)
    if match:
        repls = ('{machine_name}', args.machine_name), ('{argument}', match.group(1)), ('{value}', match.group(2))
        create_machine_conf.append(u.replace_multiple_items(repls, conf_line_template))

confp = open(args.path + 'lab.conf', 'w')
for line in create_machine_conf:
    confp.write(line)

confp.close()