import utils as u
import argparse

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')

args = parser.parse_args()

lab_path = args.path.replace('"', '')
if args.directory:
    lab_path = args.directory.replace('"', '')

print u.generate_urlsafe_hash(lab_path)