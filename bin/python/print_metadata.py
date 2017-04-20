import argparse
import netkit_commons as nc 

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser()
parser.add_argument('path')
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')

args = parser.parse_args()

lab_path = args.path.replace('"', '')
if args.directory:
    lab_path = args.directory.replace('"', '')

# get lab machines, options, links and metadata
(_,_,_, metadata) = nc.lab_parse(lab_path)

print "========================= Starting Lab =========================="
for key, value in metadata.items():
    print '{message: <20}'.format(message=key+":") + value
print "================================================================="