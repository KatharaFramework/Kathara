import argparse
import sys
from typing import List

from ..ui.utils import create_panel, interface_cd_mac
from ... import utils
from ...exceptions import PrivilegeError
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
            help='Show a help message and exit.'
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
            type=interface_cd_mac,
            dest='eths',
            metavar='N:CD/MAC',
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
        hosthome_group = self.parser.add_mutually_exclusive_group(required=False)
        hosthome_group.add_argument(
            '--no-hosthome', '-H',
            dest="hosthome_mount",
            action="store_const",
            const=False,
            help='Do not mount "/hosthome" directory inside the device.'
        )
        hosthome_group.add_argument(
            '--hosthome',
            dest="hosthome_mount",
            action="store_const",
            const=True,
            help='Mount "/hosthome" directory inside the device.'
        )
        self.parser.add_argument(
            '--xterm', '--terminal-emu',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        self.parser.add_argument(
            '--print', '--dry-run',
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
            '--env',
            dest='envs',
            metavar='ENV',
            nargs='+',
            required=False,
            help='Set environment variable for the device.'
        )
        self.parser.add_argument(
            '--ulimit',
            dest='ulimits',
            metavar='KEY=SOFT[:HARD]',
            nargs='+',
            required=False,
            help='Set ulimit for the device.'
        )
        self.parser.add_argument(
            '--shell',
            required=False,
            help='Set the shell (sh, bash, etc.) that should be used inside the device.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        name = args.pop('name')

        self.console.print(
            create_panel(
                f"Checking Device `{name}`" if args['dry_mode'] else f"Starting Device `{name}`",
                style="blue bold", justify="center"
            )
        )

        if args['dry_mode']:
            self.console.print(f"[green]\u2713 [bold]{name}[/bold] configuration is correct.")
            sys.exit(0)

        Setting.get_instance().open_terminals = args['terminals'] if args['terminals'] is not None \
            else Setting.get_instance().open_terminals
        Setting.get_instance().terminal = args['xterm'] or Setting.get_instance().terminal
        Setting.get_instance().device_shell = args['shell'] or Setting.get_instance().device_shell

        if args['privileged']:
            if not utils.is_admin():
                raise PrivilegeError("You must be root in order to start this Kathara device in privileged mode.")
            else:
                self.console.print("[yellow]\u26a0 Running devices with privileged capabilities, terminals won't open!")
                Setting.get_instance().open_terminals = False

        lab = Lab("kathara_vlab")
        lab.add_option('hosthome_mount', args['hosthome_mount'])
        lab.add_option('shared_mount', False)
        lab.add_option('privileged_machines', args['privileged'])

        device = lab.get_or_new_machine(name, **args)

        if args['eths']:
            for iface_number, cd, mac_address in args['eths']:
                try:
                    lab.connect_machine_to_link(device.name, cd,
                                                machine_iface_number=int(iface_number),
                                                mac_address=mac_address)
                except ValueError:
                    s = f"{cd}/{mac_address}" if mac_address else f"{cd}"
                    raise SyntaxError(f"Interface number in `--eth {iface_number}:{s}` is not a number.")

        Kathara.get_instance().deploy_lab(lab)
