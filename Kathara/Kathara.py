#!/usr/bin/env python

import argparse
import sys
from consolemenu import *
from consolemenu.items import *


class KatharaEntryPoint(object):

	def __init__(self):
		parser = argparse.ArgumentParser(
			description='Pretends to be Kathara',
			usage='''kathara <command> [<args>]

The possible kathara commands are:
	vstart		Start a new Kathara machine  
	vclean		Cleanup Kathara processes and configurations
	vconfig		Attach network interfaces to running Kathara machines
	vlist		Show running Kathara machines
	lstart		Start a Kathara lab 
	lclean		Stop and clean a Kathara lab  
	linfo		Show information about a Kathara lab  
	lrestart	Restart a Kathara lab
	ltest		Test a Kathara lab
	wipe		Delete all Kathara machines
	settings	Show and edit settings
	version		Print current version
	check		Check your environment
	install		Perform first run tasks
	connect		Connect to a Kathara machine
''')
		parser.add_argument('command', help='Subcommand to run')

		# parse_args defaults to [1:] for args, but you need to
		# exclude the rest of the args too, or validation will fail
		args = parser.parse_args(sys.argv[1:2])
		if not hasattr(self, args.command):
			print('Unrecognized command')
			parser.print_help()
			exit(1)
		# use dispatch pattern to invoke method with same name
		getattr(self, args.command)()

	def version(self):
		print('Current version: 0.1')

	def vstart(self):
		parser = argparse.ArgumentParser(
			prog='kathara vstart',
			description='Start a new Kathara machine.',
			epilog='Example: kathara vstart --eth 0:A 1:B -n pc1'
		)
		parser.add_argument(
			'-n', '--name',
			required=True,
			help='Name of the machine to be started'
		)
		parser.add_argument(
			'--eth', 
			dest='eths', 
			nargs='+', 
			required=True, 
			help='Set a specific interface on a collision domain.'
		)
		group = parser.add_mutually_exclusive_group(required=False)

		group.add_argument(
		    "--noterminals", 
		    action="store_const",
		    dest="terminals",
		    const=False,
		    default=True,
		    help='Start the lab without opening terminal windows.'
		)
		group.add_argument(
		    "-t", "--terminals", 
		    action="store_const",
		    dest="terminals",
		    const=True, 
		    help='Start the lab opening terminal windows.'
		)
		parser.add_argument(
			'-e', 
			'--exec',
			required=False,
			dest='exe', 
			nargs='*', 
			help='Execute a specific command in the container during startup.'
		)
		parser.add_argument(
		    '-M', '--mem',
		    required=False,
		    help='Limit the amount of RAM available for this container.'
		)
		parser.add_argument(
		    '-i', '--image',
		    required=False,
		    help='Run this container with a specific Docker image.'
		)
		parser.add_argument(
		    '-H', '--no-hosthome',
		    required=False,
		    action='store_true',
		    help='/hosthome dir will not be mounted inside the machine.'
		)
		parser.add_argument(
		    '--xterm',
		    required=False,
		    help='Set a different terminal emulator application.'
		)
		parser.add_argument(
		    '-l', '--hostlab',
		    required=False,
		    help='Set a path for a lab folder to search the specified machine.'
		)
		parser.add_argument(
		    '-p', '--print',
		    dest='print_only',
		    required=False,
		    action='store_true',
		    help='Print commands used to start the container (dry run).'
		)
		parser.add_argument(
		    '--bridged',
		    required=False,
		    action='store_true',
		    help='Adds a bridge interface to the container.'
		)
		parser.add_argument(
		    '--port',
		    required=False,
		    help='Choose a port number to map to the internal port 3000 of the container.'
		)
		parser.add_argument(
		    '--shell',
		    required=False,
		    help='Set the shell (sh, bash, etc.) that should be used inside the container.'
		)

		args = parser.parse_args(sys.argv[2:])


		print('Sta tranquillo che la eseguo sta macchina!')
		print(args)

	def lstart(self):
		# ma su netkit non si poteva fare "lstart pc1" e startava solo pc1 del lab?

		parser = argparse.ArgumentParser(
			prog='kathara lstart',
			description='Start a Kathara Lab.'
		)

		group = parser.add_mutually_exclusive_group(required=False)

		group.add_argument(
		    "-n", "--noterminals", 
		    action="store_const",
		    dest="terminals",
		    const=False,
		    default=True,
		    help='Start the lab without opening terminal windows.'
		)
		group.add_argument(
		    "-t", "--terminals", 
		    action="store_const",
		    dest="terminals",
		    const=True, 
		    help='Start the lab opening terminal windows.'
		)
		parser.add_argument(
		    '-d', '--directory',
		    required=False,
		    help='Specify the folder contining the lab.'
		)
		parser.add_argument(
		    '-F', '--force-lab',
		    dest='force_lab',
		    required=False,
		    action='store_true', 
		    help='Force the lab to start without a lab.conf or lab.dep file.'
		)
		parser.add_argument(
		    '-l', '--list',
		    required=False,
		    action='store_true', 
		    help='Show a list of running container after the lab has been started.'
		)
		parser.add_argument(
		    '-o', '--pass',
		    dest='options',
		    nargs='*',
		    required=False, 
		    help="Pass options to vstart. Options should be a list of double quoted strings, like '--pass \"mem=64m\" \"eth=0:A\"'."
		)
		parser.add_argument(
		    '--xterm',
		    required=False,
		    help='Set a different terminal emulator application (Unix only).'
		)
		parser.add_argument(
			'--print',
			dest="print_only",
			required=False,
			action='store_true',
			help='Print commands used to start the containers to stderr (dry run).'
		)
		parser.add_argument(
			'-c', '--counter',
			required=False,
			help='Start from a specific network counter (overrides whatever was previously initialized, using 0 will prompt the default behavior).'
		)
		parser.add_argument(
			"--execbash",
			required=False,
			action="store_true",
			help=argparse.SUPPRESS
		)

		args = parser.parse_args(sys.argv[2:])

		print('Sta tranquillo che lo eseguo sto lab!')
		print(args)

	def vclean(self):
		parser = argparse.ArgumentParser(
			prog='kathara vclean',
			description='Cleanup Kathara processes and configurations.',
			epilog="Example: kathara vclean pc1"
		)
		parser.add_argument(
			'machine_name',
			help='Name of the machine to be cleaned'
		)

		args = parser.parse_args(sys.argv[2:])

		print('Sta tranquillo che la cleano sta macchina!')
		print(args)

	def vconfig(self):
		parser = argparse.ArgumentParser(
			prog='kathara vconfig',
			description='Attach network interfaces to running Kathara machines.',
			epilog='Example: kathara vconfig --eth A -n pc1'
		)
		parser.add_argument(
			'-n', '--name',
			required=True,
			help='Name of the machine to be attached with the new interface.'
		)
		parser.add_argument(
			'--eth', 
			dest='eths', 
			nargs='+', 
			required=True, 
			help='Set a specific interface on a collision domain.'
		)		

		args = parser.parse_args(sys.argv[2:])

		print('Sta tranquillo che la addo sta iface!')
		print(args)

	def vlist(self):
		print('Unimplemented parameter in this version!')

	def lclean(self):
		print('Unimplemented parameter in this version!')

	def linfo(self):
		print('Unimplemented parameter in this version!')

	def ltest(self):
		print('Unimplemented parameter in this version!')

	def wipe(self):
		print('Unimplemented parameter in this version!')

	def settings(self):
		menu = ConsoleMenu("Kathara settings", "Choose the option to change")

		# MenuItem is the base class for all items, it doesn't do anything when selected
		menu_item = MenuItem("Menu Item")

		# A FunctionItem runs a Python function when selected
		function_item = FunctionItem("Call a Python function", input, ["Enter an input"])

		# A SelectionMenu constructs a menu from a list of strings
		selection_menu = SelectionMenu(["item1", "item2", "item3"])

		# A SubmenuItem lets you add a menu (the selection_menu above, for example)
		# as a submenu of another menu
		submenu_item = SubmenuItem("Submenu item", selection_menu, menu)

		menu.append_item(menu_item)
		menu.append_item(function_item)
		menu.append_item(submenu_item)

		# Finally, we call show to show the menu and allow the user to interact
		menu.show()

	def check(self):
		print('Unimplemented parameter in this version!')

	def install(self):
		print('Unimplemented parameter in this version!')

	def connect(self):
		print('Unimplemented parameter in this version!')


if __name__ == '__main__':
	KatharaEntryPoint()