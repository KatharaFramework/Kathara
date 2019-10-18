#!/usr/bin/python3

import argparse
import logging
import os
import sys

import coloredlogs
from Resources import utils
from Resources.exceptions import SettingsError, DockerDaemonConnectionError
from Resources.setting.Setting import Setting
from Resources.strings import formatted_strings
from Resources.version import CURRENT_VERSION
from Resources.auth.PrivilegeHandler import PrivilegeHandler

description_msg = """kathara [-v|--version] <command> [<args>]

The possible kathara command are:\n
%s
""" % formatted_strings()


class KatharaEntryPoint(object):
    def __init__(self):
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
            help='Print current Kathara version.',
            required=False
        )

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])

        if args.version:
            print('Current version: %s.' % CURRENT_VERSION)
            sys.exit(0)

        if args.command is None:
            parser.print_help()
            sys.exit(1)

        module_name = {
            "package": "Resources.command",
            "class": args.command.capitalize() + "Command"
        }

        try:
            # Load config file
            Setting.get_instance()
            Setting.get_instance().check()
        except (SettingsError, DockerDaemonConnectionError) as e:
            logging.critical(str(e))
            sys.exit(1)

        try:
            command_class = utils.class_for_name(module_name["package"], module_name["class"])
            command_object = command_class()
        except ModuleNotFoundError as e:
            if e.name == '.'.join(module_name.values()):
                logging.error('Unrecognized command.\n')
                parser.print_help()
                sys.exit(1)
            else:
                logging.critical("`%s` is not installed in your system\n" % e.name)
                sys.exit(1)

        try:
            current_path = os.getcwd()
            command_object.run(current_path, sys.argv[2:])
        except KeyboardInterrupt:
            logging.critical("You interrupted Kathara during a command. The system may be in an inconsistent state!")
            logging.critical("If you encounter any problem please run `kathara wipe`.")
            sys.exit(0)
        except Exception as e:
            logging.critical(str(e) + '\n')
            sys.exit(1)


if __name__ == '__main__':
    utils.check_python_version()
    utils.exec_by_platform(PrivilegeHandler.get_instance().drop_privileges, lambda: None, lambda: None)

    try:
        debug_level = Setting.get_instance().debug_level
    except SettingsError:
        debug_level = "DEBUG"

    coloredlogs.install(fmt='%(levelname)s - %(message)s', level=debug_level)
    
    KatharaEntryPoint()
