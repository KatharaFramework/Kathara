import argparse
import logging
from typing import List

from ..ui.utils import create_lab_table
from ..ui.utils import create_panel, LabMetaHighlighter
from ... import utils
from ...exceptions import PrivilegeError, EmptyLabError
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...parser.netkit.DepParser import DepParser
from ...parser.netkit.ExtParser import ExtParser
from ...parser.netkit.FolderParser import FolderParser
from ...parser.netkit.LabParser import LabParser
from ...parser.netkit.LinkParser import LinkParser
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
        self.parser.add_argument(
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
            dest='global_machine_metadata',
            metavar="METADATA",
            nargs='*',
            required=False,
            help="Apply metadata to all devices of a network scenario during startup."
        )
        self.parser.add_argument(
            '--terminal-emu',
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
            '--exclude',
            dest='excluded_machines',
            metavar='DEVICE_NAME',
            nargs='+',
            default=[],
            help='Exclude specified devices from startup.'
        )
        self.parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Launches only specified devices.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)

        # Load custom 'kathara.conf' if it exists
        self._load_custom_configuration(lab_path)

        Setting.get_instance().open_terminals = args['terminals'] if args['terminals'] is not None \
            else Setting.get_instance().open_terminals
        Setting.get_instance().terminal = args['terminal_emu'] or Setting.get_instance().terminal

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
            meta_highlighter = LabMetaHighlighter()
            self.console.print(create_panel(meta_highlighter(lab_meta_information)))

        if len(lab.machines) <= 0:
            raise EmptyLabError()

        lab.global_machine_metadata = OptionParser.parse(args['global_machine_metadata'])

        link_types, link_external_links = {}, {}
        try:
            lab_link_exists = True
            link_types, link_external_links = LinkParser.parse(lab_path)
        except FileNotFoundError:
            lab_link_exists = False

        if link_types:
            lab.assign_link_types(link_types)

        ext_external_links = {}
        try:
            lab_ext_exists = True
            ext_external_links = ExtParser.parse(lab_path) or {}

            logging.warning(
                "`lab.ext` is deprecated and will be removed in future versions. Migrate to `lab.link`."
            )
        except FileNotFoundError:
            lab_ext_exists = False

        # A collision domain can be configured in lab.link or in lab.ext, not both.
        duplicated = link_external_links.keys() & ext_external_links.keys()
        if duplicated:
            raise ValueError(
                f"Collision domains {', '.join(map(lambda x: f"`{x}`", duplicated))} "
                f"are defined in both `lab.link` and `lab.ext`."
            )

        external_links = {**ext_external_links, **link_external_links}
        if external_links:
            if not (utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2)):
                raise OSError("External links are only available on Linux systems.")
            if not utils.is_admin():
                raise PrivilegeError("You must be root in order to use external links.")

            lab.attach_external_links(external_links)

        # If dry mode, we just check if the configurations are correct.
        if args['dry_mode']:
            self.console.print("[green]\u2713 [bold]lab.conf[/bold] file is correct.")
            if dependencies:
                self.console.print("[green]\u2713 [bold]lab.dep[/bold] file is correct.")
            if lab_ext_exists:
                self.console.print("[green]\u2713 [bold]lab.ext[/bold] file is correct.")
            if lab_link_exists:
                self.console.print("[green]\u2713 [bold]lab.link[/bold] file is correct.")

            return 0

        lab.add_option('hosthome_mount', args['hosthome_mount'])
        lab.add_option('shared_mount', args['shared_mount'])

        if args['privileged'] or any(x.is_privileged() for x in lab.machines.values()):
            if not utils.is_admin():
                raise PrivilegeError("You must be root in order to start Kathara devices in privileged mode.")
            else:
                if Setting.get_instance().open_terminals:
                    self.console.print(
                        "[yellow]\u26a0 Running devices with privileged capabilities, terminals might not open!"
                    )
        lab.add_global_machine_metadata('privileged', args['privileged'])

        Kathara.get_instance().deploy_lab(
            lab, selected_machines=set(args['machine_name']), excluded_machines=set(args['excluded_machines'])
        )

        if args['list']:
            with self.console.status(
                    f"Loading...",
                    spinner="dots"
            ) as _:
                machines_stats = Kathara.get_instance().get_machines_stats(lab_hash=lab.hash)
                self.console.print(create_lab_table(machines_stats))

        return 0
