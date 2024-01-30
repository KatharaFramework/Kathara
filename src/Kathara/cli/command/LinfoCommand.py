import argparse
from typing import List

from rich import print as rich_print

from ..ui.utils import create_panel
from ..ui.utils import create_table
from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...model.Link import BRIDGE_LINK_NAME
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description
from ...trdparty.curses.curses import Curses


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

        self.parser.add_argument(
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=False,
            help='Show only information about a specified device.'
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
            else:
                self._get_lab_live_info(lab)

            return

        if args['conf']:
            self._get_conf_info(lab, machine_name=args['name'])
            return

        if args['name']:
            rich_print(
                create_panel(
                    str(next(Kathara.get_instance().get_machine_stats(args['name'], lab.hash))),
                    title=f"{args['name']} Information"
                )
            )
        else:
            machines_stats = Kathara.get_instance().get_machines_stats(lab.hash)
            print(next(create_table(machines_stats)))

    @staticmethod
    def _get_machine_live_info(lab: Lab, machine_name: str) -> None:
        # TODO: Replace Curses with rich Live
        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(
                    create_panel("Device Information") + "\n" +
                    str(next(Kathara.get_instance().get_machine_stats(machine_name, lab.hash))) + "\n"
                )
        finally:
            Curses.get_instance().close()

    @staticmethod
    def _get_lab_live_info(lab: Lab) -> None:
        machines_stats = Kathara.get_instance().get_machines_stats(lab.hash)
        table = create_table(machines_stats)

        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(next(table))
        except StopIteration:
            pass
        finally:
            Curses.get_instance().close()

    @staticmethod
    def _get_conf_info(lab: Lab, machine_name: str = None) -> None:
        if machine_name:
            rich_print(
                create_panel(
                    str(lab.machines[machine_name]),
                    title=f"{machine_name} Information"
                )
            )
            return

        lab_meta_information = str(lab)
        if lab_meta_information:
            rich_print(create_panel(lab_meta_information, title="Network Scenario Information"))

        n_machines = len(lab.machines)
        n_links = len(lab.links) if BRIDGE_LINK_NAME not in lab.links else len(lab.links) - 1

        rich_print(
            create_panel(
                f"There are {n_machines} devices.\nThere are {n_links} collision domains.",
                title="Topology Information"
            )
        )
