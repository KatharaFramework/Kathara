#!/usr/bin/env python3

import argparse
import os
import sys

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
\tsetting\t\tShow and edit setting
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
        try:
            command_class = utils.class_for_name("classes.command", args.command.capitalize() + "Command")
            command_object = command_class()
        except ModuleNotFoundError:
            sys.stderr.write('Unrecognized command.\n')
            parser.print_help()
            exit(1)

        try:
            # Load config file
            Setting.get_instance()

            current_path = os.getcwd()
            command_object.run(current_path, sys.argv[2:])
        except KeyboardInterrupt:
            print("You interrupted Kathara during a command. The system may be in an inconsistent state!")
            print("If you encounter any problem please run `kathara wipe`.")
            exit(0)
        except Exception as e:
            import traceback

            traceback.print_exc()

            sys.stderr.write(str(e) + '\n')
            exit(1)


if __name__ == '__main__':
    KatharaEntryPoint()
