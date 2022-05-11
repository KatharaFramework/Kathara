import argparse
from typing import List

from ..ui.utils import create_table
from ..ui.utils import format_headers
from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
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
            help='Show an help message and exit.'
        )

        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            '-l', '--live',
            required=False,
            action='store_true',
            help='Live mode, can be used only when a lab is launched.'
        )

        group.add_argument(
            '-c', '--conf',
            required=False,
            action='store_true',
            help='Read information from lab.conf.'
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
        lab_hash = utils.generate_urlsafe_hash(lab_path)

        if args['live']:
            if args['name']:
                self._get_machine_live_info(lab_hash, args['name'])
            else:
                self._get_lab_live_info(lab_hash)

            return

        if args['conf']:
            self._get_conf_info(lab_path, machine_name=args['name'])
            return

        if args['name']:
            print(format_headers("Device Information"))
            print(str(next(Kathara.get_instance().get_machine_stats(args['name'], lab_hash))))
            print(format_headers())
        else:
            machines_stats = Kathara.get_instance().get_machines_stats(lab_hash)
            print(next(create_table(machines_stats)))

    @staticmethod
    def _get_machine_live_info(lab_hash: str, machine_name: str) -> None:
        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(
                    format_headers("Device Information") + "\n" +
                    str(next(Kathara.get_instance().get_machine_stats(machine_name, lab_hash))) + "\n" +
                    format_headers()
                )
        finally:
            Curses.get_instance().close()

    @staticmethod
    def _get_lab_live_info(lab_hash: str) -> None:
        machines_stats = Kathara.get_instance().get_machines_stats(lab_hash)
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
    def _get_conf_info(lab_path: str, machine_name: str = None) -> None:
        lab = LabParser.parse(lab_path)
        if machine_name:
            print(format_headers("Device Information"))
            print(str(lab.machines[machine_name]))
            print(format_headers())
            return

        print(format_headers("Network Scenario Information"))
        lab_meta_information = str(lab)

        if lab_meta_information:
            print(lab_meta_information)
            print(format_headers())

        n_machines = len(lab.machines)
        n_links = len(lab.links) if BRIDGE_LINK_NAME not in lab.links else len(lab.links) - 1

        print("There are %d devices." % n_machines)
        print("There are %d collision domains." % n_links)

        print(format_headers())
