#!/usr/bin/env python3

import argparse
import os
import sys
import coloredlogs, logging

import utils
from classes.setting.Setting import Setting

description_msg = """kathara <command> [<args>]

The possible kathara command are:
\tvstart\t\tStart a new Kathara machine
\tvclean\t\tCleanup Kathara processes and configurations
\tvconfig\t\tAttach network interfaces to running Kathara machines
\tlstart\t\tStart a Kathara lab
\tlclean\t\tStop and clean a Kathara lab
\tlinfo\t\tShow information about a Kathara lab
\tlrestart\tRestart a Kathara lab
\tltest\t\tTest a Kathara lab
\tconnect\t\tConnect to a Kathara machine
\twipe\t\tDelete all Kathara machines and links
\tlist\t\tShow all running Kathara machines
\tsettings\tShow and edit setting
\tversion\t\tPrint current version
\tcheck\t\tCheck your system environment
"""


class KatharaEntryPoint(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Pretends to be Kathara',
                                         usage=description_msg
                                         )

        parser.add_argument('command', help='Subcommand to run.')

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])

        command_object = None

        module_name = ("classes.command", args.command.capitalize() + "Command")
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
            # import traceback
            # traceback.print_exc()
            # Cambiare in logging.critical per non stampare stacktrace
            logging.exception(str(e) + '\n')
            sys.exit(1)


if __name__ == '__main__':
    coloredlogs.install(fmt='%(levelname)s - %(message)s', level='INFO')
    
    KatharaEntryPoint()
