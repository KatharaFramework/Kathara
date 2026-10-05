import argparse
import os
from typing import List

from ..ui.utils import create_panel
from ... import utils
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...parser.netkit.LabParser import LabParser
from ...strings import strings, wiki_description


class SaveCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara save',
            description=strings['save'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show a help message and exit.'
        )

        group = self.parser.add_mutually_exclusive_group(required=False)
        group.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the running network scenario to save.'
        )
        group.add_argument(
            '-n', '--name',
            required=False,
            help='Save a running network scenario by its name.'
        )
        self.parser.add_argument(
            '-o', '--output',
            required=False,
            help='Path of the save file to create (default: `<name>.tar` in the current directory).'
        )
        mode_group = self.parser.add_mutually_exclusive_group(required=False)
        mode_group.add_argument(
            '--diff',
            dest='filesystem_diff',
            action='store_const',
            const=True,
            default=True,
            help='Save only the filesystem changes of each device relative to its base image (default). '
                 'Produces a smaller file, but the base images must be available on restore.'
        )
        mode_group.add_argument(
            '--full-images',
            dest='filesystem_diff',
            action='store_const',
            const=False,
            help='Save the full committed image of each device. Produces a larger but self-contained file.'
        )
        self.parser.add_argument(
            '--exclude',
            dest='excluded_machines',
            metavar='DEVICE_NAME',
            nargs='+',
            default=[],
            help='Exclude specified devices from the save.'
        )
        self.parser.add_argument(
            'machine_names',
            metavar='DEVICE_NAME',
            nargs='*',
            help='Save only specified devices.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        self.console.print(create_panel("Saving Network Scenario", style="blue bold", justify="center"))

        selected_machines = set(args['machine_names']) if args['machine_names'] else None
        excluded_machines = set(args['excluded_machines']) if args['excluded_machines'] else None

        if args['name']:
            save_name = args['name']
            target_kwargs = {'lab_name': args['name']}
        else:
            lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
            lab_path = utils.get_absolute_path(lab_path)

            # Load custom 'kathara.conf' if it exists
            self._load_custom_configuration(lab_path)

            try:
                lab = LabParser.parse(lab_path)
            except (Exception, IOError):
                lab = Lab(None, path=lab_path)

            save_name = lab.name or os.path.basename(lab_path) or "kathara_lab"
            target_kwargs = {'lab': lab}

        archive_path = args['output'] or os.path.join(current_path, f"{save_name}.tar")
        archive_path = utils.get_absolute_path(archive_path)

        Kathara.get_instance().save_lab(
            archive_path, selected_machines=selected_machines, excluded_machines=excluded_machines,
            filesystem_diff=args['filesystem_diff'], **target_kwargs
        )

        self.console.print(f"[green]✓ Network scenario saved to [bold]{archive_path}[/bold].")

        return 0
