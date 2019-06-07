import argparse
import sys

from k8s import lab_deployer


def commandline_arg(bytestring):
    try:
        unicode_string = bytestring.decode(sys.getfilesystemencoding())
        return unicode_string
    except AttributeError:
        return bytestring

parser = argparse.ArgumentParser(description='Clean Netkit Lab deployments on Kubernetes cluster.')
parser.add_argument('path', type=commandline_arg)
parser.add_argument(
    '-d', '--directory',
    required=False,
    help='Specify the folder containing the lab.'
)
parser.add_argument(
    '-A', '--all',
    required=False,
    action='store_true',
    help='All labs deployed on cluster are deleted.'
)

args, unknown = parser.parse_known_args()

lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else \
           args.path.replace('"', '').replace("'", '')

if not args.all:
    machine_name_args = list(filter(lambda x: not (x.startswith("--") or x.startswith("-")), unknown))
    lab_deployer.delete(lab_path, machine_name_args)
else:
    lab_deployer.delete_all(lab_path)
