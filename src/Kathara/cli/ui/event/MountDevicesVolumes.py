import logging

from rich.console import Console
from rich.tree import Tree

from ...ui.utils import confirmation_prompt
from ....model.Lab import Lab
from ....model.Machine import Machine
from ....setting.Setting import Setting


class MountDevicesVolumes(object):
    """Listener fired when devices have volumes to mount."""

    def run(self, lab: Lab, machines_with_volumes: dict[str, Machine]) -> None:
        """Prompt the user for confirming devices volumes.

        Args:
            lab (Lab): The network scenario.
            machines_with_volumes (dict[str, Machine]): Dict containing Machine objects with volumes attached.

        Returns:
            None
        """
        console = Console()
        console.print("The following devices have volumes configured:")
        for machine_name, machine in machines_with_volumes.items():
            tree = Tree(f"* [cyan]Device `{machine_name}`[/cyan]")
            for host_path, volume in machine.meta["volumes"].items():
                guest_path = volume.get("guest_path", "<missing guest_path>")
                tree.add(f"Host Path: [green]{host_path}[/green] -> Device Path: [magenta]{guest_path}[/magenta]")
            console.print(tree)

        policy = Setting.get_instance().volume_mount_policy
        if policy == 'Prompt':
            confirmation_prompt(
                "Continue with volume mounting?",
                lambda: None,
                lambda: lab.add_option("_mount_volumes", False)
            )
