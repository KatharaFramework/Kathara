import argparse

import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..model.Lab import Lab
from ..setting.Setting import Setting


class VstartCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vstart',
            description='Start a new Kathara machine.',
            epilog='Example: kathara vstart --eth 0:A 1:B -n pc1'
        )

        group = parser.add_mutually_exclusive_group(required=False)

        group.add_argument(
            "--noterminals",
            action="store_const",
            dest="terminals",
            const=False,
            default=None,
            help='Start the machine without opening a terminal window.'
        )
        group.add_argument(
            "-t", "--terminals",
            action="store_const",
            dest="terminals",
            const=True,
            help='Start the machine opening its terminal window.'
        )
        parser.add_argument(
            '-n', '--name',
            required=True,
            help='Name of the machine to be started.'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            nargs='+',
            required=False,
            help='Set a specific interface on a collision domain.'
        )
        parser.add_argument(
            '-e', '--exec',
            required=False,
            dest='exec_commands',
            nargs='*',
            help='Execute a specific command in the machine during startup.'
        )
        parser.add_argument(
            '-M', '--mem',
            required=False,
            help='Limit the amount of RAM available for this machine.'
        )
        parser.add_argument(
            '-i', '--image',
            required=False,
            help='Run this machine with a specific Docker image.'
        )
        parser.add_argument(
            '-H', '--no-hosthome',
            dest="no_hosthome",
            required=False,
            action='store_false',
            help='/hosthome dir will not be mounted inside the machine.'
        )
        parser.add_argument(
            '--xterm',
            required=False,
            help='Set a different terminal emulator application (Unix only).'
        )
        parser.add_argument(
            '-p', '--print',
            dest='dry_mode',
            required=False,
            action='store_true',
            help='Check if the machine parameters are correct (dry run).'
        )
        parser.add_argument(
            '--bridged',
            required=False,
            action='store_true',
            help='Add a bridge interface to the machine.'
        )
        parser.add_argument(
            '--port',
            required=False,
            help='Choose a port number to map to the internal port 3000 of the machine.'
        )
        parser.add_argument(
            '--shell',
            required=False,
            help='Set the shell (sh, bash, etc.) that should be used inside the machine.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        if args.dry_mode:
            print("Machine configuration is correct. Exiting...")
            exit(0)
        else:
            print("========================= Starting Machine ==========================")

        vlab_dir = utils.get_vlab_temp_path()
        lab = Lab(vlab_dir)

        machine = lab.get_or_new_machine(args.name)

        if args.eths:
            for eth in args.eths:
                try:
                    (iface_number, link_name) = eth.split(":")
                    lab.connect_machine_to_link(machine.name, int(iface_number), link_name)
                except ValueError:
                    raise Exception("Interface number in `--eth %s` is not a number." % eth)

        if args.exec_commands:
            for command in args.exec_commands:
                machine.add_meta("exec", command)

        if args.mem:
            machine.add_meta("mem", args.mem)

        if args.image:
            machine.add_meta("image", args.image)

        if args.bridged:
            machine.add_meta("bridged", True)

        if args.port:
            machine.add_meta("port", args.port)

        Setting.get_instance().open_terminals = args.terminals if args.terminals is not None \
                                                else Setting.get_instance().open_terminals

        Setting.get_instance().terminal = args.xterm or Setting.get_instance().terminal
        Setting.get_instance().machine_shell = args.shell or Setting.get_instance().machine_shell
        Setting.get_instance().hosthome_mount = args.no_hosthome if args.no_hosthome is not None \
                                                else Setting.get_instance().hosthome_mount

        ManagerProxy.get_instance().deploy_lab(lab)

        Setting.get_instance().save_selected(['net_counter'])
