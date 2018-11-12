import utils as u
import argparse
import netkit_commons as nc
import re

DEBUG = nc.DEBUG
nc.DEBUG = False
non_ascii = r'[^\x00-\x7F]+'

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')
parser.add_argument(
    '--print',
    dest="print_only",
    required=False,
    action='store_true',
    help='Print commands used to start the containers to stderr (containers are not started).'
)

args, unknown = parser.parse_known_args()

lab_path = args.path.replace('"', '').replace("'", '').replace("//", '/')
if args.directory:
    lab_path = args.directory.replace('"', '').replace("'", '').replace("//", '/')

lab_path = re.sub(non_ascii,'', lab_path)

if args.print_only and nc.PLATFORM == nc.WINDOWS: #linux still needs the hash for the while statement
    print(" ")
else:
    print(u.generate_urlsafe_hash(lab_path))
