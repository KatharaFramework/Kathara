import sys
import netkit_commons as nc
import argparse

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser()
parser.add_argument('path')

args = parser.parse_args()
args.path = args.path.replace('"', '')

has_invalid_characters = False
(machines, links, _, _) = nc.lab_parse(args.path)
for machine_name, _ in machines.items():
    if (' ' in machine_name) or ('"' in machine_name) or ("'" in machine_name):
        has_invalid_characters = True
        break
if not has_invalid_characters:    
    for link in links:
        if (' ' in link) or ('"' in link) or ("'" in link):
            has_invalid_characters = True
            break

if has_invalid_characters:  
    print "Invalid characters in machine names or link names\n"
    sys.exit(1)

if sys.version_info >= (3, 0):
    print "Requires Python 2.x, not Python 3.x\n"
    sys.exit(1)