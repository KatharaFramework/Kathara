import argparse
import os
import sys
from typing import List

from ..ui.utils import create_panel
from ..ui.utils import create_table
from ... import utils
from ...exceptions import PrivilegeError, EmptyLabError
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...parser.netkit.DepParser import DepParser
from ...parser.netkit.ExtParser import ExtParser
from ...parser.netkit.FolderParser import FolderParser
from ...parser.netkit.LabParser import LabParser
from ...parser.netkit.OptionParser import OptionParser
from ...setting.Setting import Setting
from ...strings import strings, wiki_description


class LstartCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara lstart',
            description=strings['lstart'],
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
            help='Start the network scenario without opening terminal windows.'
        )
        group.add_argument(
            "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the network scenario opening terminal windows.'
        )
        group.add_argument(
            "--privileged",
            action="store_const",
            const=True,
            required=False,
            help='Start the devices in privileged mode. MUST BE ROOT FOR THIS OPTION.'
        )
        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the network scenario.'
        )
        self.parser.add_argument(
            '-F', '--force-lab',
            dest='force_lab',
            required=False,
            action='store_true',
            help='Force the network scenario to start without a lab.conf or lab.dep file.'
        )
        self.parser.add_argument(
            '-l', '--list',
            required=False,
            action='store_true',
            help='Show information about running devices after the network scenario has been started.'
        )
        self.parser.add_argument(
            '-o', '--pass',
            dest='options',
            metavar="OPTION",
            nargs='*',
            required=False,
            help="Apply options to all devices of a network scenario during startup."
        )
        self.parser.add_argument(
            '--xterm', '--terminal-emu',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        self.parser.add_argument(
            '--print', '--dry-mode',
            dest="dry_mode",
            required=False,
            action='store_true',
            help='Open the lab.conf file and check if it is correct (dry run).'
        )
        hosthome_group = self.parser.add_mutually_exclusive_group(required=False)
        hosthome_group.add_argument(
            '--no-hosthome', '-H',
            dest="hosthome_mount",
            action="store_const",
            const=False,
            help='Do not mount "/hosthome" directory inside devices.'
        )
        hosthome_group.add_argument(
            '--hosthome',
            dest="hosthome_mount",
            action="store_const",
            const=True,
            help='Mount "/hosthome" directory inside devices.'
        )
        shared_group = self.parser.add_mutually_exclusive_group(required=False)
        shared_group.add_argument(
            '--no-shared', '-S',
            dest="shared_mount",
            action="store_const",
            const=False,
            help='Do not mount "/shared" directory inside devices.'
        )
        shared_group.add_argument(
            '--shared',
            dest="shared_mount",
            action="store_const",
            const=True,
            help='Mount "/shared" directory inside devices.'
        )
        self.parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Launches only specified devices.'
        )

    def run(self, current_path: str, argv: List[str]) -> Lab:
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)

        Setting.get_instance().open_terminals = args['terminals'] if args['terminals'] is not None \
            else Setting.get_instance().open_terminals
        Setting.get_instance().terminal = args['xterm'] or Setting.get_instance().terminal

        self.console.print(
            create_panel(
                "Checking Network Scenario" if args['dry_mode'] else "Starting Network Scenario",
                style="blue bold", justify="center"
            )
        )

        try:
            lab = LabParser.parse(lab_path)
        except IOError as e:
            if not args['force_lab']:
                raise e
            else:
                lab = FolderParser.parse(lab_path)

        # Reorder machines by lab.dep file, if present.
        dependencies = DepParser.parse(lab_path)
        if dependencies:
            lab.apply_dependencies(dependencies)

        lab_meta_information = str(lab)
        if lab_meta_information:
            self.console.print(create_panel(lab_meta_information))

        if len(lab.machines) <= 0:
            raise EmptyLabError()

        try:
            options = OptionParser.parse(args['options'])
            lab.general_options = {**lab.general_options, **options}
        except ValueError as e:
            raise e

        lab_ext_path = os.path.join(lab_path, 'lab.ext')
        lab_ext_exists = False
        if os.path.exists(lab_ext_path):
            lab_ext_exists = True
            if utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2):
                if utils.is_admin():
                    external_links = ExtParser.parse(lab_path)

                    if external_links:
                        lab.attach_external_links(external_links)

                        # Since xterm does not work with "sudo", we do not open terminals when lab.ext is present.
                        Setting.get_instance().open_terminals = False
                else:
                    raise PrivilegeError("You must be root in order to use lab.ext file.")
            else:
                raise OSError("lab.ext is only available on UNIX systems.")

        # If dry mode, we just check if the lab.conf is correct.
        if args['dry_mode']:
            self.console.print("[green]\u2713 [bold]lab.conf[/bold] file is correct.")
            if dependencies:
                self.console.print("[green]\u2713 [bold]lab.dep[/bold] file is correct.")
            if lab_ext_exists:
                self.console.print("[green]\u2713 [bold]lab.ext[/bold] file is correct.")

            sys.exit(0)

        lab.add_option('hosthome_mount', args['hosthome_mount'])
        lab.add_option('shared_mount', args['shared_mount'])
        lab.add_option('privileged_machines', args['privileged'])

        if args['privileged']:
            if not utils.is_admin():
                raise PrivilegeError("You must be root in order to start Kathara devices in privileged mode.")
            else:
                self.console.print("[yellow]\u26a0 Running devices with privileged capabilities, terminals won't open!")
                Setting.get_instance().open_terminals = False

        Kathara.get_instance().deploy_lab(lab, selected_machines=set(args['machine_name']))

        if args['list']:
            machines_stats = Kathara.get_instance().get_machines_stats(lab_hash=lab.hash)
            print(next(create_table(machines_stats)))

        return lab
