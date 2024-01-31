import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Generator, Optional
from typing import Callable

from rich import box
from rich.console import RenderableType, Group
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from ... import utils
from ...foundation.manager.stats.IMachineStats import IMachineStats
from ...setting.Setting import Setting
from ...utils import parse_cd_mac_address

FORBIDDEN_TABLE_COLUMNS = ["container_name"]


def confirmation_prompt(prompt_string: str, callback_yes: Callable, callback_no: Callable) -> Any:
    answer = Confirm.ask(prompt_string)
    if not answer:
        return callback_no()

    return callback_yes()


def create_panel(message: str = "", **kwargs) -> Panel:
    return Panel(
        Text(
            message,
            style=kwargs['style'] if 'style' in kwargs else "none",
            justify=kwargs['justify'] if 'justify' in kwargs else None,
        ),
        title=kwargs['title'] if 'title' in kwargs else None,
        title_align="center",
        box=kwargs['box'] if 'box' in kwargs else box.SQUARE,
    )


def create_table(streams: Generator[Dict[str, IMachineStats], None, None]) -> Optional[RenderableType]:
    try:
        result = next(streams)
    except StopIteration:
        return None

    ts_header = f"TIMESTAMP: {datetime.now()}"
    if not result:
        return Group(
            Text(ts_header, style="italic", justify="center"),
            create_panel("No Devices Found", style="red bold", justify="center", box=box.DOUBLE)
        )

    table = Table(title=ts_header, show_lines=True, expand=True, box=box.SQUARE_DOUBLE_HEAD)

    for item in result.values():
        row_data = item.to_dict()
        row_data = dict(filter(lambda x: x[0] not in FORBIDDEN_TABLE_COLUMNS, row_data.items()))

        if not table.columns:
            for col in map(lambda x: x.replace('_', ' ').upper(), row_data.keys()):
                table.add_column(col, header_style="blue")

        table.add_row(*map(lambda x: str(x), row_data.values()))

    return table


def open_machine_terminal(machine) -> None:
    """Connect to the device with the terminal specified in the settings.

    Returns:
        None
    """
    Setting.get_instance().check_terminal()
    terminal = Setting.get_instance().terminal

    logging.debug("Opening terminal for device %s.", machine.name)

    executable_path = utils.get_executable_path(sys.argv[0])

    if not executable_path:
        raise FileNotFoundError("Unable to find Kathara.")

    is_vmachine = "-v" if not machine.lab.has_host_path() else ""
    connect_command = "%s connect %s -l %s" % (executable_path, is_vmachine, machine.name)

    logging.debug("Terminal will open in directory %s." % machine.lab.fs_path())

    def unix_connect() -> None:
        if terminal == "TMUX":
            from ...trdparty.libtmux.tmux import TMUX

            logging.debug("Attaching `%s` to TMUX session `%s` with command `%s`" % (machine.name, machine.lab.name,
                                                                                     connect_command))

            TMUX.get_instance().add_window(
                machine.lab.name,
                machine.name,
                connect_command,
                cwd=machine.lab.fs_path()
            )
        else:
            logging.debug("Opening Linux terminal with command: %s." % connect_command)

            # Command should be passed as an array
            # https://stackoverflow.com/questions/9935151/popen-error-errno-2-no-such-file-or-directory/9935511
            subprocess.Popen([terminal, "-e", connect_command],
                             cwd=machine.lab.fs_path(),
                             start_new_session=True
                             )

    def windows_connect() -> None:
        complete_win_command = "& %s" % connect_command
        logging.debug("Opening Windows terminal with command: %s." % complete_win_command)
        subprocess.Popen(["powershell.exe",
                          '-Command',
                          complete_win_command
                          ],
                         creationflags=subprocess.CREATE_NEW_CONSOLE,
                         cwd=machine.lab.fs_path()
                         )

    def osx_connect() -> None:
        cd_to_lab_path = "cd \"%s\" &&" % machine.lab.fs_path() if machine.lab.has_host_path() else ""
        complete_osx_command = "%s clear && %s && exit" % (cd_to_lab_path, connect_command)

        if terminal == "TMUX":
            from ...trdparty.libtmux.tmux import TMUX

            logging.debug("Attaching `%s` to TMUX session `%s` with command `%s`" % (machine.name, machine.lab.name,
                                                                                     complete_osx_command))

            TMUX.get_instance().add_window(
                machine.lab.name,
                machine.name,
                complete_osx_command,
                cwd=machine.lab.fs_path()
            )
        else:
            import appscript
            logging.debug("Opening OSX terminal with command: %s." % complete_osx_command)
            terminal_app = appscript.app(terminal)
            if terminal == 'iTerm':
                window = terminal_app.create_window_with_default_profile()
                window.current_session.write(text=complete_osx_command)
            elif terminal == 'Terminal':
                terminal_app.do_script(complete_osx_command)

    utils.exec_by_platform(unix_connect, windows_connect, osx_connect)


# Types for argparse
def alphanumeric(value, pat=re.compile(r"^\w+$")):
    if not pat.match(value):
        raise argparse.ArgumentTypeError("invalid alphanumeric value")

    return value


def interface_cd_mac(value):
    n, cd, mac = None, None, None
    try:
        parts = value.split('/')
        (n, cd) = parts[0].split(':')
        if len(parts) == 2:
            if parts[1]:
                mac = parts[1]
            else:
                raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError("invalid interface definition: %s" % value)

    if not re.search(r"^\w+$", cd):
        raise argparse.ArgumentTypeError(f"invalid interface definition, "
                                         f"collision domain `{cd}` contains non-alphanumeric characters")

    return n, cd, mac


def cd_mac(value):
    return parse_cd_mac_address(value)
