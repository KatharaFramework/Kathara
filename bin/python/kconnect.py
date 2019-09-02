import argparse
import sys

import netkit_commons as nc
from k8s import connection_proxy

nc.DEBUG = False


def commandline_arg(bytestring):
    try:
        unicode_string = bytestring.decode(sys.getfilesystemencoding())
        return unicode_string
    except AttributeError:
        return bytestring

parser = argparse.ArgumentParser(description='Connect to a remote machine in Kubernetes.')
parser.add_argument('path', type=commandline_arg)
parser.add_argument(
    '-d', '--directory',
    required=False,
    help='Specify the folder containing the lab.'
)

args, unknown = parser.parse_known_args()

lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else \
           args.path.replace('"', '').replace("'", '')

machine_name_arg = list(filter(lambda x: not (x.startswith("--") or x.startswith("-")), unknown))

if machine_name_arg:
    print connection_proxy.connect_to_pod(machine_name_arg[0], lab_path)
else:
    sys.stderr.write("You should specify a machine name.")
