import argparse

from .. import utils
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..setting.Setting import Setting
from ..strings import strings, wiki_description
from ..trdparty.libtmux.tmux import TMUX


class LcleanCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara lclean',
            description=strings['lclean'],
            epilog=wiki_description,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            'machine_names',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Clean only specified machines.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        lab_hash = utils.generate_urlsafe_hash(lab_path)

        ManagerProxy.get_instance().undeploy_lab(lab_hash,
                                                 selected_machines=args.machine_names
                                                 )

        if "tmux" in Setting.get_instance().terminal:
            TMUX.get_instance().kill_instance()
