#!/usr/bin/env python

import argparse
import os
import sys

import utils
from classes.setting.Setting import Setting

description_msg = """kathara <command> [<args>]

The possible kathara command are:
	vstart		Start a new Kathara machine
	vclean		Cleanup Kathara processes and configurations
	vconfig		Attach network interfaces to running Kathara machines
	vlist		Show running Kathara machines
	lstart		Start a Kathara lab
	lclean		Stop and clean a Kathara lab
	linfo		Show information about a Kathara lab
	lrestart	Restart a Kathara lab
	ltest		Test a Kathara lab
	wipe		Delete all Kathara machines and links
	setting		Show and edit setting
	version		Print current version
	check		Check your environment
	install		Perform first run tasks
	connect		Connect to a Kathara machine
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
        except Exception as e:
            sys.stderr.write(str(e) + '\n')
            exit(1)


if __name__ == '__main__':
    KatharaEntryPoint()
