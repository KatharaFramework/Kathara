import argparse
from typing import List

from ..ui.utils import alphanumeric, cd_mac, cd_mode, create_panel
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
from ...strings import strings, wiki_description


class VconfigCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara vconfig',
            description=strings['vconfig'],
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
            '-n', '--name',
            metavar='DEVICE_NAME',
            required=True,
            help='Name of the device to be connected on desired collision domains.'
        )

        group = self.parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            '--add',
            type=cd_mac,
            dest='to_add',
            metavar='CD[/MAC][/vlan=ID][/trunk=ID,...]',
            nargs='+',
            help='Specify the collision domain to add. '
                 'On a managed collision domain, `vlan` is the VLAN of the untagged frames of the interface '
                 'and `trunk` lists the VLANs exchanged tagged.'
        )
        group.add_argument(
            '--rm',
            type=alphanumeric,
            dest='to_remove',
            metavar='CD',
            nargs='+',
            help='Specify the collision domain to remove.'
        )
        self.parser.add_argument(
            '--cd-mode',
            type=cd_mode,
            dest='cd_modes',
            metavar='CD:MODE',
            nargs='+',
            required=False,
            help='Set the mode of a collision domain: hub (default), switch or managed. '
                 'Only for a collision domain which is created by the command.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        self.parse_args(argv)
        args = self.get_args()

        lab = Lab("kathara_vlab")
        Kathara.get_instance().update_lab_from_api(lab)

        machine_name = args['name']
        device = lab.get_machine(machine_name)
        device.api_object = Kathara.get_instance().get_machine_api_object(machine_name, lab_name=lab.name)

        self.console.print(
            create_panel(f"Updating Device `{machine_name}`", style="blue bold", justify="center")
        )

        if args['to_add']:
            cd_modes = dict(args['cd_modes'] or [])
            for cd_name, mac_address, vlans in args['to_add']:
                self.console.print(
                    f"[green]+ Adding interface to device `{machine_name}` on collision domain `{cd_name}`" +
                    (f" with MAC Address {mac_address}" if mac_address else "") +
                    f"..."
                )
                link = lab.get_or_new_link(cd_name)
                if cd_name in cd_modes:
                    link.mode = cd_modes[cd_name]
                Kathara.get_instance().connect_machine_to_link(device, link, mac_address=mac_address, **vlans)

        if args['to_remove']:
            for cd_to_remove in args['to_remove']:
                self.console.print(
                    f"[red]- Removing interface on collision domain `{cd_to_remove}` from device `{machine_name}`..."
                )
                link = lab.get_link(cd_to_remove)
                link.api_object = Kathara.get_instance().get_link_api_object(cd_to_remove, lab_name=lab.name)

                Kathara.get_instance().disconnect_machine_from_link(device, link)

        return 0
