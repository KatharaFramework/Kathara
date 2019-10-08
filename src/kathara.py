#!/usr/bin/python3

import argparse
import logging
import os
import sys

import coloredlogs
from Resources import utils
from Resources.setting.Setting import Setting
from Resources.version import CURRENT_VERSION

description_msg = """kathara <command> [<args>]

The possible kathara command are:
\tvstart\t\tStart a new Kathara machine
\tvclean\t\tCleanup Kathara processes and configurations
\tvconfig\t\tAttach network interfaces to a running Kathara machine
\tlstart\t\tStart a Kathara lab
\tlclean\t\tStop and clean a Kathara lab
\tlinfo\t\tShow information about a Kathara lab
\tlrestart\tRestart a Kathara lab
\tltest\t\tTest a Kathara lab
\tconnect\t\tConnect to a Kathara machine
\twipe\t\tDelete all Kathara machines and links, optionally also delete settings
\tlist\t\tShow all running Kathara machines
\tsettings\tShow and edit Kathara settings
\tcheck\t\tCheck your system environment
"""


class KatharaEntryPoint(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Pretends to be Kathara',
                                         usage=description_msg
                                         )

        parser.add_argument('command',
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
            args.command = ""

        module_name = ("Resources.command", args.command.capitalize() + "Command")
        try:
            command_class = utils.class_for_name(module_name[0], module_name[1])
            command_object = command_class()
        except ModuleNotFoundError as e:
            if e.name == '.'.join(module_name):
                logging.error('Unrecognized command.\n')
                parser.print_help()
                sys.exit(1)
            else:
                logging.critical("\nLooks like %s is not installed in your system\n" % e.name)
                sys.exit(1)

        try:
            # Load config file
            Setting.get_instance()
            Setting.get_instance().check()

            current_path = os.getcwd()
            command_object.run(current_path, sys.argv[2:])
        except KeyboardInterrupt:
            logging.critical("You interrupted Kathara during a command. The system may be in an inconsistent state!")
            logging.critical("If you encounter any problem please run `kathara wipe`.")
            sys.exit(0)
        except Exception as e:
            # TODO: Cambiare in logging.critical per non stampare stacktrace
            logging.exception(str(e) + '\n')
            sys.exit(1)


if __name__ == '__main__':
    coloredlogs.install(fmt='%(levelname)s - %(message)s', level=Setting.get_instance().debug_level)
    
    KatharaEntryPoint()
