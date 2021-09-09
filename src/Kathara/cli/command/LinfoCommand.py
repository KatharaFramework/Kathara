import argparse
from typing import List

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
            if args['name']:
                print(Kathara.get_instance().get_formatted_machine_info(args['name'], lab_hash))
            else:
                self._get_conf_info(lab_path)

            return

        if args['name']:
            print(Kathara.get_instance().get_formatted_machine_info(args['name'], lab_hash))
        else:
            lab_info = Kathara.get_instance().get_formatted_lab_info(lab_hash)

            print(next(lab_info))

    @staticmethod
    def _get_machine_live_info(lab_hash, machine_name):
        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(
                    Kathara.get_instance().get_formatted_machine_info(machine_name, lab_hash)
                )
        finally:
            Curses.get_instance().close()

    @staticmethod
    def _get_lab_live_info(lab_hash: str) -> None:
        lab_info = Kathara.get_instance().get_formatted_lab_info(lab_hash)

        Curses.get_instance().init_window()

        try:
            while True:
                Curses.get_instance().print_string(next(lab_info))
        except StopIteration:
            pass
        finally:
            Curses.get_instance().close()

    @staticmethod
    def _get_conf_info(lab_path: str) -> None:
        print(utils.format_headers("Lab Information"))

        lab = LabParser.parse(lab_path)
        lab_meta_information = str(lab)

        if lab_meta_information:
            print(lab_meta_information)
            print(utils.format_headers())

        n_machines = len(lab.machines)
        n_links = len(lab.links) if BRIDGE_LINK_NAME not in lab.links else len(lab.links) - 1

        print("There are %d devices." % n_machines)
        print("There are %d collision domains." % n_links)

        print(utils.format_headers())
