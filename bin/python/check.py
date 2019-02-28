import sys
import netkit_commons as nc
import argparse
import os
try:
    import pwd
except ImportError: #windows
    pass

DEBUG = nc.DEBUG
nc.DEBUG = False

parser = argparse.ArgumentParser()
parser.add_argument('path')
parser.add_argument('-d', '--directory', required=False, help='Folder contining the lab.')
parser.add_argument('-f', '--full', required=False, action="store_true")
parser.add_argument(
    '-F', '--force-lab',
    dest='force_lab',
    required=False,
    action='store_true', 
    help='Force the lab to start without a lab.conf or lab.dep file.'
)

args, unknown = parser.parse_known_args()

lab_path = args.path.replace('"', '').replace("'", '')
if args.directory:
    lab_path = args.directory.replace('"', '').replace("'", '')

if args.full:
    has_invalid_characters = False
    (machines, links, _, _) = nc.lab_parse(lab_path, force=args.force_lab)
    for machine_name, _ in list(machines.items()):
        if (' ' in machine_name) or ('"' in machine_name) or ("'" in machine_name):
            has_invalid_characters = True
            break
    if not has_invalid_characters:    
        for link in links:
            if (' ' in link) or ('"' in link) or ("'" in link):
                has_invalid_characters = True
                break

    if has_invalid_characters:  
        print ("Invalid characters in machine names or link names\n")
        sys.exit(1)

if nc.PLATFORM != nc.WINDOWS:
    if pwd.getpwuid(os.getuid()).pw_dir != os.environ['HOME']:
        print ("HOME variable is different from the real home directory. This won't allow labs to work.\n")
        print("Please set HOME=" + pwd.getpwuid(os.getuid().pw_dir + "\n"))
        sys.exit(1)