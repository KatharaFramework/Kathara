import argparse
import re
import sys

from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
import utils
from ..model.Lab import Lab
from ..setting.Setting import Setting


class VconfigCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vconfig',
            description='Attach network interfaces to running Kathara machines.',
            epilog='Example: kathara vconfig --eth A -n pc1'
        )
        parser.add_argument(
            '-n', '--name',
            required=True,
            help='Name of the machine to be attached with the new interface.'
        )
        parser.add_argument(
            '--eth',
            dest='eths',
            nargs='+',
            required=True,
            help='Set an interface on a collision domain.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        #Controllo se eths ha solo i caratteri accettati
        for eth in args.eths:
            matches = re.search(r"^\w+$", eth)

            if not matches:
                sys.stderr.write('Syntax error in --eth field.\n')
                self.parser.print_help()

        vlab_dir = utils.get_vlab_temp_path()
        lab = Lab(vlab_dir)

        ManagerProxy.get_instance().attach_links_to_machine(lab, args.name, args.eths)

        Setting.get_instance().save_selected(['net_counter'])