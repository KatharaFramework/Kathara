import base64
import hashlib
import argparse

parser = argparse.ArgumentParser(description='Create and start a Netkit Lab.')
parser.add_argument('path')

args = parser.parse_args()

print (base64.urlsafe_b64encode(hashlib.md5(args.path).digest()))[:-2]