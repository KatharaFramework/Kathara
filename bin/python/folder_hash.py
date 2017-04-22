import utils as u
import argparse

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')
parser.add_argument(
    '--print',
    dest="print_only",
    required=False,
    action='store_true',
    help='Print commands used to start the containers (containers are not started).'
)

args, unknown = parser.parse_known_args()

lab_path = args.path.replace('"', '').replace("'", '')
if args.directory:
    lab_path = args.directory.replace('"', '').replace("'", '')

if not args.print_only:
    print u.generate_urlsafe_hash(lab_path)