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

parser = argparse.ArgumentParser(description='Retrieve lab information from the Kubernetes cluster. By default, '
                                             'only machines information are printed.')
parser.add_argument('path', type=commandline_arg)
parser.add_argument(
    '-d', '--directory',
    required=False,
    help='Specify the folder containing the lab.'
)
parser.add_argument(
    '-l', '--links',
    required=False,
    action="store_true",
    help='Prints only the links of the lab.'
)
parser.add_argument(
    '-n', '--namespace',
    required=False,
    action="store_true",
    help='Prints only the namespace of the lab.'
)
parser.add_argument(
    '-a', '--all',
    required=False,
    action="store_true",
    help='Prints all the information (both machine and links) of the lab.'
)


args = parser.parse_args()

lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else \
           args.path.replace('"', '').replace("'", '')

lab_deployer.get_lab_info(lab_path,
                          only_links=args.links,
                          only_namespace=args.namespace,
                          print_all=args.all
                          )
