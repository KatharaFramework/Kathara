import argparse
import sys

import netkit_commons as nc
from k8s import connection_proxy

nc.DEBUG = False

parser = argparse.ArgumentParser(description='Connect to a remote machine in Kubernetes.')
parser.add_argument(
    '-n', '--namespace',
    help='Lab namespace where the machine is running.'
)

args, unknown = parser.parse_known_args()

machine_name_arg = list(filter(lambda x: not (x.startswith("--") or x.startswith("-")), unknown))
if machine_name_arg:
    connection_proxy.connect_to_pod(machine_name_arg[0], args.namespace)
else:
    sys.stderr.write("You should specify a machine name.")
