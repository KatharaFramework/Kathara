#!/usr/bin/env python3

import argparse
import logging
import multiprocessing
import os
import sys

import coloredlogs

from Kathara import utils
from Kathara.auth.PrivilegeHandler import PrivilegeHandler
from Kathara.exceptions import SettingsError, DockerDaemonConnectionError, ClassNotFoundError
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
            sys.exit(0)

        if args.command is None or not args.command.islower():
            parser.print_help()
            sys.exit(1)

        try:
            # Check settings
            Setting.get_instance().check()
        except (SettingsError, DockerDaemonConnectionError) as e:
            logging.critical(str(e))
            sys.exit(1)

        try:
            command_object = CommandFactory().create_instance(class_args=(args.command.capitalize(),))
        except ClassNotFoundError:
            logging.error('Unrecognized command `%s`.\n' % args.command)
            parser.print_help()
            sys.exit(1)
        except ImportError as e:
            logging.critical("`%s` is not installed in your system\n" % e.name)
            sys.exit(1)

        try:
            current_path = os.getcwd()
            command_object.run(current_path, sys.argv[2:])
        except KeyboardInterrupt:
            if args.command not in ['exec', 'linfo', 'list', 'settings']:
                logging.warning("You interrupted Kathara during a command. The system may be in an inconsistent "
                                "state!\n")
                logging.warning("If you encounter any problem please run `kathara wipe`.")
            sys.exit(0)
        except Exception as e:
            if Setting.get_instance().debug_level == "EXCEPTION":
                logging.exception(str(e) + '\n')
            else:
                logging.critical(str(e) + '\n')
            sys.exit(1)


if __name__ == '__main__':
    multiprocessing.freeze_support()

    utils.CLI_ENV = True
    utils.check_python_version()

    utils.exec_by_platform(PrivilegeHandler.get_instance().drop_privileges, lambda: None, lambda: None)

    try:
        debug_level = Setting.get_instance().debug_level
        debug_level = debug_level if debug_level != "EXCEPTION" else "DEBUG"
    except SettingsError:
        debug_level = "DEBUG"

    coloredlogs.install(fmt='%(levelname)s - %(message)s', level=debug_level)

    KatharaEntryPoint()
