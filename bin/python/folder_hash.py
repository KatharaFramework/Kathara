import utils as u
import argparse

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')

args = parser.parse_args()

print u.generate_urlsafe_hash(args.path)