from ..utils import open_machine_terminal
from ....model import Machine as MachinePackage
from ....setting.Setting import Setting


class OpenMachineTerminal(object):
    """Listener fired when a device is deployed and started."""

    def run(self, item: 'MachinePackage.Machine') -> None:
        """
        If allowed, open a terminal, with the emulator specified in the settings, into the device.

        Args:
            item (Kathara.model.Machine): Machine instance where open a terminal.

        Returns:
            None
        """
        if Setting.get_instance().open_terminals:
            for i in range(0, item.get_num_terms()):
                open_machine_terminal(item)
