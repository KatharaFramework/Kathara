import os
import sys

from ..utils import open_machine_terminal
from .... import utils
from ....model import Machine as MachinePackage
from ....setting.Setting import Setting


class HandleMachineTerminal(object):
    """Listener fired when a device is deployed and started."""

    def run(self, item: 'MachinePackage.Machine') -> None:
        """If allowed, open a terminal, with the emulator specified in the settings, into the device.

        Args:
            item (Kathara.model.Machine): Device where open a terminal.

        Returns:
            None
        """
        if Setting.get_instance().open_terminals:
            for i in range(0, item.get_num_terms()):
                open_machine_terminal(item)

    def flush(self) -> None:
        """Clean the stdout buffer.

        Returns:
            None
        """

        def flush_unix():
            sys.stdout.write("\033[2J")
            sys.stdout.write("\033[0;0H")
            sys.stdout.flush()

        def flush_win():
            os.system('cls')

        utils.exec_by_platform(flush_unix, flush_win, flush_unix)

    def print_wait_msg(self) -> None:
        """Print the startup commands waiting message.

        Returns:
            None
        """
        sys.stdout.write("Waiting startup commands execution. Press [ENTER] to override...")
        sys.stdout.flush()
