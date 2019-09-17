import argparse

import utils
from ..controller.Controller import Controller
from ..foundation.command.Command import Command


class VcleanCommand(Command):
    __slots__ = []

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara vclean',
            description='Stops a Kathara machine.',
            epilog="Example: kathara vclean -n pc1"
        )

        parser.add_argument(
            '-n', '--name',
            required=True,
            help='Name of the machine to be cleaned.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        vlab_dir = utils.get_vlab_temp_path()
        lab_hash = utils.generate_urlsafe_hash(vlab_dir)

        Controller.get_instance().undeploy_lab(lab_hash,
                                               selected_machines=[args.name]
                                               )
