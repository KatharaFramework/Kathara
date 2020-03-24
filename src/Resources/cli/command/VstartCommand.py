import argparse
import logging
import re
import sys

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.ManagerProxy import ManagerProxy
from ...model.Lab import Lab
from ...setting.Setting import Setting
from ...strings import strings, wiki_description


class VstartCommand(Command):
    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vstart',
            description=strings['vstart'],
            epilog=wiki_description,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        group = parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=None,
            help='Start the machine without opening a terminal window.'
        )
        group.add_argument(
            "-t", "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the machine opening its terminal window.'
        )
        parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the machine to be started.'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            metavar='N:CD',
            nargs='+',
            required=False,
            help='Set a specific interface on a collision domain.'
        )
        parser.add_argument(
            '-e', '--exec',
            required=False,
            dest='exec_commands',
            nargs='*',
            help='Execute a specific command in the machine during startup.'
        )
        parser.add_argument(
            '--mem',
            required=False,
            help='Limit the amount of RAM available for this machine.'
        )
        parser.add_argument(
            '--cpus',
            required=False,
            help='Limit the amount of CPU available for this machine.'
        )
        parser.add_argument(
            '-i', '--image',
            required=False,
            help='Run this machine with a specific Docker Image.'
        )
        parser.add_argument(
            '-H', '--no-hosthome',
            dest="no_hosthome",
            required=False,
            action='store_false',
            help='/hosthome dir will not be mounted inside the machine.'
        )
        group.add_argument(
            "--privileged",
            action="store_true",
            required=False,
            help='Start the device in privileged mode. MUST BE ROOT FOR THIS OPTION.'
        )
        parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        parser.add_argument(
            '--print',
            dest='dry_mode',
            required=False,
            action='store_true',
            help='Check if the machine parameters are correct (dry run).'
        )
        parser.add_argument(
            '--bridged',
            required=False,
            action='store_true',
            help='Add a bridge interface to the machine.'
        )
        parser.add_argument(
            '--port',
            required=False,
            help='Choose a TCP Port number to map localhost port PORT to the internal port 3000 of the machine.'
        )
        parser.add_argument(
            '--shell',
            required=False,
            help='Set the shell (sh, bash, etc.) that should be used inside the machine.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        self.parse_args(argv)
        args = self.get_args()

        if args.dry_mode:
            print("Machine configuration is correct. Exiting...")
            sys.exit(0)
        else:
            print(utils.format_headers("Starting Machine"))

        args.no_shared = False

        Setting.get_instance().open_terminals = args.terminals if args.terminals is not None \
                                                else Setting.get_instance().open_terminals
        Setting.get_instance().terminal = args.xterm or Setting.get_instance().terminal
        Setting.get_instance().device_shell = args.shell or Setting.get_instance().device_shell

        if args.privileged:
            if not utils.is_admin():
                raise Exception("You must be root in order to start this Kathara device in privileged mode.")
            else:
                logging.warning("Running device with privileged capabilities, terminal won't open!")
                Setting.get_instance().open_terminals = False

        vlab_dir = utils.get_vlab_temp_path()
        lab = Lab(vlab_dir)

        machine_name = args.name.strip()
        matches = re.search(r"^[a-z0-9_]{1,30}$", machine_name)
        if not matches:
            raise Exception("Invalid machine name `%s`." % machine_name)

        machine = lab.get_or_new_machine(machine_name)

        if args.eths:
            for eth in args.eths:
                try:
                    (iface_number, link_name) = eth.split(":")
                    lab.connect_machine_to_link(machine.name, int(iface_number), link_name)
                except ValueError:
                    raise Exception("Interface number in `--eth %s` is not a number." % eth)

        if args.exec_commands:
            for command in args.exec_commands:
                machine.add_meta("exec", command)

        if args.mem:
            machine.add_meta("mem", args.mem)

        if args.cpus:
            machine.add_meta("cpus", args.cpus)

        if args.image:
            machine.add_meta("image", args.image)

        if args.bridged:
            machine.add_meta("bridged", True)

        if args.port:
            machine.add_meta("port", args.port)

        ManagerProxy.get_instance().deploy_lab(lab)
