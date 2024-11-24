#!/usr/bin/env python3

import argparse
import logging
import multiprocessing
import os
import sys

from rich.logging import RichHandler

from Kathara import utils
from Kathara.auth.PrivilegeHandler import PrivilegeHandler
from Kathara.cli.ui.event.register import register_cli_events, unregister_cli_events
from Kathara.exceptions import SettingsError, DockerDaemonConnectionError, ClassNotFoundError, SettingsNotFoundError
from Kathara.foundation.cli.command.CommandFactory import CommandFactory
from Kathara.setting.Setting import Setting
from Kathara.strings import formatted_strings
from Kathara.version import CURRENT_VERSION

description_msg = """kathara [-h] [-v] <command> [<args>]

Possible Kathara commands are:\n
%s
""" % formatted_strings()


class KatharaEntryPoint(object):
    def __init__(self) -> None:
        parser = argparse.ArgumentParser(
            description='A network emulation tool.',
            usage=description_msg,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        parser.add_argument(
            'command',
            help='Command to run.',
            nargs="?"
        )

        parser.add_argument(
            "-v", "--version",
            action="store_true",
            help='Print the current Kathara version.',
            required=False
        )

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])

        if args.version:
            print('Current version: %s' % CURRENT_VERSION)
            unregister_cli_events()
            sys.exit(0)

        if args.command is None or not args.command.islower():
            parser.print_help()
            unregister_cli_events()
            sys.exit(1)

        try:
            # Check settings only if the user is not executing "settings" command.
            if "settings" not in args.command:
                Setting.get_instance().check()
        except (SettingsError, DockerDaemonConnectionError) as e:
            logging.critical(f"({type(e).__name__}) {str(e)}")
            unregister_cli_events()
            sys.exit(1)

        try:
            command_object = CommandFactory().create_instance(class_args=(args.command.capitalize(),))
        except ClassNotFoundError:
            logging.error(f"Unrecognized command `{args.command}`.")
            parser.print_help()
            unregister_cli_events()
            sys.exit(1)
        except ImportError as e:
            logging.critical(f"({type(e).__name__}) `{e.name}` is not installed in your system")
            unregister_cli_events()
            sys.exit(1)

        try:
            current_path = os.getcwd()
            exit_code = command_object.run(current_path, sys.argv[2:])
            unregister_cli_events()

            sys.exit(exit_code)
        except KeyboardInterrupt:
            if args.command not in ['exec', 'linfo', 'list', 'settings']:
                logging.warning("You interrupted Kathara during a command. The system may be in an inconsistent "
                                "state! If you encounter any problem please run `kathara wipe`.")
            unregister_cli_events()
            sys.exit(0)
        except Exception as e:
            if Setting.get_instance().debug_level == "EXCEPTION":
                logging.exception(f"({type(e).__name__}) {str(e)}")
            else:
                logging.critical(f"({type(e).__name__}) {str(e)}")
            unregister_cli_events()
            sys.exit(1)


if __name__ == '__main__':
    try:
        Setting.get_instance().load_from_disk()
    except SettingsNotFoundError:
        Setting.get_instance().save_to_disk()

    try:
        debug_level = Setting.get_instance().debug_level
        debug_level = debug_level if debug_level != "EXCEPTION" else "DEBUG"
    except SettingsError:
        debug_level = "DEBUG"

    logging.basicConfig(
        level=debug_level, format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False, show_path=False)]
    )

    multiprocessing.freeze_support()

    register_cli_events()

    utils.check_python_version()

    utils.exec_by_platform(PrivilegeHandler.get_instance().drop_privileges, lambda: None, lambda: None)

    KatharaEntryPoint()
