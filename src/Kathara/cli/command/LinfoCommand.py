import argparse
from typing import List

from rich.live import Live

from ..ui.utils import create_lab_table
from ..ui.utils import create_panel, LabMetaHighlighter, create_topology_table
from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...model.Link import BRIDGE_LINK_NAME
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description


class LinfoCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara linfo',
            description=strings['linfo'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show a help message and exit.'
        )

        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the network scenario.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            '-w', '-l', '--watch', '--live',
            required=False,
            action='store_true',
            help='Watch mode, can be used only when a network scenario is launched.'
        )

        group.add_argument(
            '-c', '--conf',
            required=False,
            action='store_true',
            help='Read static information from lab.conf.'
        )

        topology_group = self.parser.add_mutually_exclusive_group(required=False)

        topology_group.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=False,
            help='Show only information about a specified device.'
        )

        topology_group.add_argument(
            '-t', '--topology',
            required=False,
            action='store_true',
            help='Get running topology info'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)
        try:
            lab = LabParser.parse(lab_path)
        except (Exception, IOError):
            lab = Lab(None, path=lab_path)

        if args['watch']:
            if args['name']:
                self._get_machine_live_info(lab, args['name'])
            elif args['topology']:
                self._get_live_topology_info(lab)
            else:
                self._get_lab_live_info(lab)

            return

        if args['conf']:
            self._get_conf_info(lab, machine_name=args['name'])
            return

        with self.console.status(
                f"Loading...",
                spinner="dots"
        ) as _:
            if args['name']:
                machine_stats = next(Kathara.get_instance().get_machine_stats(args['name'], lab.hash))
                message = str(machine_stats) if machine_stats else f"Device `{args['name']}` Not Found."
                style = None if machine_stats else "red bold"

                self.console.print(create_panel(message, title=f"{args['name']} Information", style=style))
            elif args['topology']:
                Kathara.get_instance().update_lab_from_api(lab)
                self.console.print(create_topology_table(lab))
            else:
                machines_stats = Kathara.get_instance().get_machines_stats(lab.hash)
                self.console.print(create_lab_table(machines_stats))

    def _get_machine_live_info(self, lab: Lab, machine_name: str) -> None:
        with Live(None, refresh_per_second=12.5, screen=True) as live:
            live.update(self.console.status(f"Loading...", spinner="dots"))
            live.refresh_per_second = 1
            while True:
                machine_stats = next(Kathara.get_instance().get_machine_stats(machine_name, lab.hash))
                message = str(machine_stats) if machine_stats else f"Device `{machine_name}` Not Found."
                style = None if machine_stats else "red bold"

                live.update(create_panel(message, title=f"{machine_name} Information", style=style))

    def _get_live_topology_info(self, lab: Lab) -> None:
        with Live(None, refresh_per_second=1, screen=True) as live:
            live.update(self.console.status(f"Loading...", spinner="dots"))
            while True:
                Kathara.get_instance().update_lab_from_api(lab)
                table = create_topology_table(lab)
                if not table:
                    break

                live.update(table)

    def _get_lab_live_info(self, lab: Lab) -> None:
        machines_stats = Kathara.get_instance().get_machines_stats(lab.hash)

        with Live(None, refresh_per_second=12.5, screen=True) as live:
            live.update(self.console.status(f"Loading...", spinner="dots"))
            live.refresh_per_second = 1
            while True:
                table = create_lab_table(machines_stats)
                if not table:
                    break

                live.update(table)

    def _get_conf_info(self, lab: Lab, machine_name: str = None) -> None:
        if machine_name:
            self.console.print(
                create_panel(
                    str(lab.machines[machine_name]),
                    title=f"{machine_name} Information"
                )
            )
            return

        lab_meta_information = str(lab)
        if lab_meta_information:
            meta_highlighter = LabMetaHighlighter()
            self.console.print(
                create_panel(
                    meta_highlighter(lab_meta_information),
                    title="Network Scenario Information",
                )
            )

        n_machines = len(lab.machines)
        n_links = len(lab.links) if BRIDGE_LINK_NAME not in lab.links else len(lab.links) - 1

        self.console.print(
            create_panel(
                f"There are [bold green]{n_machines}[/bold green] devices.\n"
                f"There are [bold green]{n_links}[/bold green] collision domains.",
                title="Topology Information"
            )
        )
