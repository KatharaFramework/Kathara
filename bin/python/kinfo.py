import argparse
import sys

import netkit_commons as nc
from k8s import lab_deployer

nc.DEBUG = False


def commandline_arg(bytestring):
    try:
        unicode_string = bytestring.decode(sys.getfilesystemencoding())
        return unicode_string
    except AttributeError:
        return bytestring

parser = argparse.ArgumentParser(description='Retrieve lab deployment information from the Kubernetes cluster.')
parser.add_argument('path', type=commandline_arg)
parser.add_argument(
    '-d', '--directory',
    required=False,
    help='Specify the folder containing the lab.'
)

args = parser.parse_args()

lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else \
           args.path.replace('"', '').replace("'", '')

lab_deployer.get_lab_info(lab_path)
