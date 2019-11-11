import argparse
import os
import sys

from .. import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..parser.netkit.DepParser import DepParser
from ..parser.netkit.ExtParser import ExtParser
from ..parser.netkit.FolderParser import FolderParser
from ..parser.netkit.LabParser import LabParser
from ..parser.netkit.OptionParser import OptionParser
from ..setting.Setting import Setting
from ..strings import strings, wiki_description


class LstartCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lstart',
            description=strings['lstart'],
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
            "-n", "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=None,
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
            help='Show information about running machines after the lab has been started.'
        )
        parser.add_argument(
            '-o', '--pass',
            dest='options',
            metavar="OPTION",
            nargs='*',
            required=False,
            help="Apply options to all machines of a lab during startup."
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
            help='Open the lab.conf file and check if it is correct (dry run).'
        )
        parser.add_argument(
            '-H', '--no-hosthome',
            dest="no_hosthome",
            required=False,
            action='store_false',
            help='/hosthome dir will not be mounted inside the machine.'
        )
        parser.add_argument(
            '-S', '--no-shared',
            dest="no_shared",
            required=False,
            action='store_false',
            help='/shared dir will not be mounted inside the machine.'
        )
        parser.add_argument(
            'machine_name',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Launches only specified machines.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        Setting.get_instance().open_terminals = args.terminals if args.terminals is not None \
                                                else Setting.get_instance().open_terminals
        Setting.get_instance().terminal = args.xterm or Setting.get_instance().terminal
        Setting.get_instance().hosthome_mount = args.no_hosthome if args.no_hosthome is not None \
                                                else Setting.get_instance().hosthome_mount
        Setting.get_instance().shared_mount = args.no_shared if args.no_shared is not None \
                                              else Setting.get_instance().shared_mount

        if args.dry_mode:
            print(utils.format_headers("Checking Lab"))
        else:
            print(utils.format_headers("Starting Lab"))

        try:
            lab = LabParser.parse(lab_path)
        except FileNotFoundError as e:
            if not args.force_lab:
                raise Exception(str(e))
            else:
                lab = FolderParser.parse(lab_path)

        # Reorder machines by lab.dep file, if present.
        dependencies = DepParser.parse(lab_path)
        if dependencies:
            lab.apply_dependencies(dependencies)

        lab_ext_path = os.path.join(lab_path, 'lab.ext')

        if os.path.exists(lab_ext_path):
            if utils.is_platform(utils.LINUX) or utils.is_platform(utils.LINUX2):
                if utils.is_admin():
                    external_links = ExtParser.parse(lab_path)

                    if external_links:
                        lab.attach_external_links(external_links)

                        # Since xterm does not work with "sudo", we do not open terminals when lab.ext is present.
                        Setting.get_instance().open_terminals = False
                else:
                    raise Exception("You must be root in order to use lab.ext file.")
            else:
                raise Exception("lab.ext is only available on UNIX systems.")

        if args.machine_name:
            lab.intersect_machines(args.machine_name)

        lab_meta_information = str(lab)

        if lab_meta_information:
            print(lab_meta_information)
            print("=============================================================")

        # If dry mode, we just check if the lab.conf is correct.
        if args.dry_mode:
            print("lab.conf file is correct. Exiting...")
            sys.exit(0)

        if len(lab.machines) <= 0:
            raise Exception("No machines in the current lab. Exiting...")

        try:
            lab.general_options = OptionParser.parse(args.options)
        except:
            raise Exception("--pass parameter not valid.")

        ManagerProxy.get_instance().deploy_lab(lab)

        if args.list:
            print(next(ManagerProxy.get_instance().get_lab_info(lab.folder_hash)))
