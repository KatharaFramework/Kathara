import argparse
import logging
import sys
from typing import List

from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...setting.Setting import Setting
from ...strings import strings, wiki_description


class VstartCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara vstart',
            description=strings['vstart'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=None,
            help='Start the device without opening a terminal window.'
        )
        group.add_argument(
            "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the device opening its terminal window.'
        )
        group.add_argument(
            "--privileged",
            action="store_const",
            const=True,
            required=False,
            help='Start the device in privileged mode. MUST BE ROOT FOR THIS OPTION.'
        )
        group.add_argument(
            '--num_terms',
            metavar='NUM_TERMS',
            required=False,
            help='Choose the number of terminals to open for the device.'
        )
        self.parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the device to be started.'
        )
        self.parser.add_argument(
            '--eth',
            dest='eths',
            metavar='N:CD',
            nargs='+',
            required=False,
            help='Set a specific interface on a collision domain.'
        )
        self.parser.add_argument(
            '-e', '--exec',
            required=False,
            dest='exec_commands',
            nargs='*',
            help='Execute a specific command in the device during startup.'
        )
        self.parser.add_argument(
            '--mem',
            required=False,
            help='Limit the amount of RAM available for this device.'
        )
        self.parser.add_argument(
            '--cpus',
            required=False,
            help='Limit the amount of CPU available for this device.'
        )
        self.parser.add_argument(
            '-i', '--image',
            required=False,
            help='Run this device with a specific Docker Image.'
        )
        self.parser.add_argument(
            '-H', '--no-hosthome',
            dest="no_hosthome",
            action="store_const",
            const=False,
            help='/hosthome dir will not be mounted inside the device.'
        )
        self.parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        self.parser.add_argument(
            '--print',
            dest='dry_mode',
            required=False,
            action='store_true',
            help='Check if the device parameters are correct (dry run).'
        )
        self.parser.add_argument(
            '--bridged',
            required=False,
            action='store_true',
            help='Add a bridge interface to the device.'
        )
        self.parser.add_argument(
            '--port',
            dest='ports',
            metavar='[HOST:]GUEST[/PROTOCOL]',
            nargs='+',
            required=False,
            help='Map localhost port HOST to the internal port GUEST of the device for the specified PROTOCOL.'
        )
        self.parser.add_argument(
            '--sysctl',
            dest='sysctls',
            metavar='SYSCTL',
            nargs='+',
            required=False,
            help='Set sysctl option for the device.'
        )
        self.parser.add_argument(
            '--shell',
            required=False,
            help='Set the shell (sh, bash, etc.) that should be used inside the device.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        if args['dry_mode']:
            logging.info("Device configuration is correct. Exiting...")
            sys.exit(0)
        else:
            logging.info(utils.format_headers("Starting Device"))

        Setting.get_instance().open_terminals = args['terminals'] if args['terminals'] is not None \
            else Setting.get_instance().open_terminals
        Setting.get_instance().terminal = args['xterm'] or Setting.get_instance().terminal
        Setting.get_instance().device_shell = args['shell'] or Setting.get_instance().device_shell

        if args['privileged']:
            if not utils.is_admin():
                raise Exception("You must be root in order to start this Kathara device in privileged mode.")
            else:
                logging.warning("Running device with privileged capabilities, terminal won't open!")
                Setting.get_instance().open_terminals = False

        lab = Lab("kathara_vlab")
        lab.add_option('hosthome_mount', args['no_hosthome'])
        lab.add_option('shared_mount', False)
        lab.add_option('privileged_machines', args['privileged'])

        name = args.pop('name')

        device = lab.get_or_new_machine(name, **args)

        if args['eths']:
            for eth in args['eths']:
                try:
                    (iface_number, link_name) = eth.split(":")
                    lab.connect_machine_to_link(device.name, link_name, machine_iface_number=int(iface_number))
                except ValueError:
                    raise Exception("Interface number in `--eth %s` is not a number." % eth)

        lab.check_integrity()

        Kathara.get_instance().deploy_lab(lab)
