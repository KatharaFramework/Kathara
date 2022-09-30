import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Generator
from typing import Callable

from terminaltables import DoubleTable

from ... import utils
from ...foundation.manager.stats.IMachineStats import IMachineStats
from ...setting.Setting import Setting
from ...trdparty.consolemenu import PromptUtils, Screen

FORBIDDEN_TABLE_COLUMNS = ["container_name"]


def confirmation_prompt(prompt_string: str, callback_yes: Callable, callback_no: Callable) -> Any:
    prompt_utils = PromptUtils(Screen())
    answer = prompt_utils.prompt_for_bilateral_choice(prompt_string, 'y', 'n')

    if answer == "n":
        return callback_no()

    return callback_yes()


def format_headers(message: str = "") -> str:
    footer = "=============================="
    half_message = int((len(message) / 2) + 1)
    second_half_message = half_message

    if len(message) % 2 == 0:
        second_half_message -= 1

    message = " " + message + " " if message != "" else "=="
    return footer[half_message:] + message + footer[second_half_message:]


def create_table(streams: Generator[Dict[str, IMachineStats], None, None]) -> \
        Generator[str, None, None]:
    table = DoubleTable([])
    table.inner_row_border = True

    while True:
        try:
            result = next(streams)
        except StopIteration:
            return

        if not result:
            return

        table.table_data = []
        for item in result.values():
            row_data = item.to_dict()
            row_data = dict(filter(lambda x: x[0] not in FORBIDDEN_TABLE_COLUMNS, row_data.items()))

            if not table.table_data:
                table.table_data.append(list(map(lambda x: x.replace('_', ' ').upper(), row_data.keys())))

            table.table_data.append(row_data.values())

        yield "TIMESTAMP: %s" % datetime.now() + "\n\n" + table.table


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

    is_vmachine = "-v" if machine.lab.path is None else ""
    connect_command = "%s connect %s -l %s" % (executable_path, is_vmachine, machine.name)

    logging.debug("Terminal will open in directory %s." % machine.lab.path)

    def unix_connect() -> None:
        if terminal == "TMUX":
            from ...trdparty.libtmux.tmux import TMUX

            logging.debug("Attaching `%s` to TMUX session `%s` with command `%s`" % (machine.name, machine.lab.name,
                                                                                     connect_command))

            TMUX.get_instance().add_window(machine.lab.name, machine.name, connect_command, cwd=machine.lab.path)
        else:
            logging.debug("Opening Linux terminal with command: %s." % connect_command)

            # Command should be passed as an array
            # https://stackoverflow.com/questions/9935151/popen-error-errno-2-no-such-file-or-directory/9935511
            subprocess.Popen([terminal, "-e", connect_command],
                             cwd=machine.lab.path,
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
                         cwd=machine.lab.path
                         )

    def osx_connect() -> None:
        cd_to_lab_path = "cd \"%s\" &&" % machine.lab.path if machine.lab.path is not None else ""
        complete_osx_command = "%s clear && %s && exit" % (cd_to_lab_path, connect_command)

        if terminal == "TMUX":
            from ...trdparty.libtmux.tmux import TMUX

            logging.debug("Attaching `%s` to TMUX session `%s` with command `%s`" % (machine.name, machine.lab.name,
                                                                                     complete_osx_command))

            TMUX.get_instance().add_window(machine.lab.name, machine.name, complete_osx_command, cwd=machine.lab.path)
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


def colon_separated(value):
    try:
        (v1, v2) = value.split(':')
    except ValueError:
        raise argparse.ArgumentTypeError("invalid colon-separated value: %s" % value)

    return v1, v2
