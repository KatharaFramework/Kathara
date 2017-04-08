import argparse
import netkit_commons as nc 

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser()
parser.add_argument('path')

args = parser.parse_args()

# get lab machines, options, links and metadata
(_,_,_, metadata) = nc.lab_parse(args.path)

print "========================= Starting Lab =========================="
for key, value in metadata.items():
    print '{message: <20}'.format(message=key+":") + value
print "================================================================="