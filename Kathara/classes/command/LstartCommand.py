import argparse

import utils
from .Command import Command
from ..deployer.Deployer import Deployer
from ..parser.FolderParser import FolderParser
from ..parser.LabParser import LabParser
from ..parser.OptionParser import OptionParser
from ..setting.Setting import Setting


class LstartCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lstart',
            description='Starts a Kathara lab.'
        )

        group = parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "-n", "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=True,
            help='Start the lab without opening terminal windows.'
        )
        group.add_argument(
            "-t", "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the lab opening terminal windows.'
        )
        parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            '-F', '--force-lab',
            dest='force_lab',
            required=False,
            action='store_true',
            help='Force the lab to start without a lab.conf or lab.dep file.'
        )
        parser.add_argument(
            '-l', '--list',
            required=False,
            action='store_true',
            help='Show a list of running machines after the lab has been started.'
        )
        parser.add_argument(
            '-o', '--pass',
            dest='options',
            nargs='*',
            required=False,
            help="Pass options to vstart. Options should be a list of double quoted strings, "
                 "like '--pass \"mem=64m\" \"image=kathara/netkit_base\"'."
        )
        parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        parser.add_argument(
            '--print',
            dest="dry_mode",
            required=False,
            action='store_true',
            help='Opens the lab.conf file and check if it is correct (dry run).'
        )
        parser.add_argument(
            '-c', '--counter',
            required=False,
            help='Start from a specific network counter '
                 '(overrides whatever was previously initialized).'
        )
        parser.add_argument(
            'machine_names',
            nargs='*',
            help='Launches only specified machines.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        if args.dry_mode:
            print("========================= Checking Lab ==========================")
        else:
            print("========================= Starting Lab ==========================")

        try:
            lab = LabParser.parse(lab_path)
        except FileNotFoundError as e:
            if not args.force_lab:
                raise Exception(str(e))
            else:
                lab = FolderParser.parse(lab_path)

        lab.intersect(args.machine_names)

        lab_meta_information = str(lab)

        if lab_meta_information:
            print(lab_meta_information)
            print("=================================================================")

        # If dry mode, we just check if the lab.conf is correct.
        if args.dry_mode:
            print("lab.conf file is correct. Exiting...")
            exit(0)

        try:
            parsed_options = OptionParser.parse(args.options)
        except:
            raise Exception("--pass parameter not valid.")

        if args.counter:
            try:
                Setting.get_instance().net_counter = int(args.counter)
                Setting.get_instance().check_net_counter()
            except ValueError:
                raise Exception("Network Counter must be an integer.")

        terminals = args.terminals if args.terminals is not None else Setting.get_instance().open_terminals
        Deployer.get_instance().deploy_lab(lab,
                                           terminals=terminals,
                                           options=parsed_options,
                                           xterm=args.xterm or Setting.get_instance().terminal
                                           )

        if not args.counter:
            Setting.get_instance().save_selected(['net_counter'])

        if args.list:
            Deployer.get_instance().get_info_stream(lab.folder_hash)
