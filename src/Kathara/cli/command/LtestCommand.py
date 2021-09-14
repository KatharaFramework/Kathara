import argparse
import logging
import os
import shutil
import sys
import time
from typing import List

from .LcleanCommand import LcleanCommand
from .LstartCommand import LstartCommand
from ... import utils
from ...exceptions import TestError
from ...foundation.cli.command.Command import Command
from ...strings import strings, wiki_description
from ...test.BuiltinTest import BuiltInTest
from ...test.UserTest import UserTest


class LtestCommand(Command):
    def __init__(self) -> None:
        Command.__init__(self)

        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog='kathara ltest',
            description=strings['ltest'],
            epilog=wiki_description,
            add_help=False
        )

        self.parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        self.parser.add_argument(
            '-R', '--rebuild-signature',
            dest="rebuild_signature",
            required=False,
            action='store_true',
            help='Force generating a new signature for the lab, even if one already exists. '
                 'Overwrites any existing signature.'
        )
        self.parser.add_argument(
            '--wait',
            required=False,
            metavar='MINUTES',
            help='Minutes to wait from lab startup before running the tests (can be a decimal number).'
        )
        self.parser.add_argument(
            '--verify',
            required=False,
            choices=['builtin', 'user', 'both'],
            help='Compares current lab state with stored signature.'
        )

    def run(self, current_path: str, argv: List[str]) -> None:
        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)

        signature_test_path = None
        if not args['verify']:
            signature_test_path = os.path.join(lab_path, "_test", "signature")

            if os.path.exists(signature_test_path) and not args['rebuild_signature']:
                logging.error("Signature for current lab already exists. Exiting...")
                sys.exit(1)

        # Tests run without terminals, no shared and /hosthome dirs.
        new_argv = ["--noterminals", "--no-shared", "--no-hosthome"]

        # Start the lab
        lab = LstartCommand().run(lab_path, new_argv)

        if args['wait']:
            try:
                sleep_minutes = float(args['wait'])
                if sleep_minutes < 0:
                    raise ValueError()

                logging.info("Waiting %s minutes before running tests..." % sleep_minutes)
                time.sleep(sleep_minutes * 60)
            except ValueError:
                raise ValueError("--wait value is not valid!")

        # Run Tests and store in signature
        builtin_test = BuiltInTest(lab)
        user_test = UserTest(lab)

        builtin_test_passed = True
        user_test_passed = True

        if not args['verify']:
            if not os.path.exists(signature_test_path) or args['rebuild_signature']:
                shutil.rmtree(signature_test_path, ignore_errors=True)
                os.makedirs(signature_test_path, exist_ok=True)

                builtin_test.create_signature()
                user_test.create_signature()
        else:
            result_test_path = os.path.join(lab.path, "_test", "results")

            shutil.rmtree(result_test_path, ignore_errors=True)
            os.makedirs(result_test_path, exist_ok=True)

            try:
                if args['verify'] == "builtin" or args['verify'] == "both":
                    builtin_test_passed = builtin_test.test()
                if args['verify'] == "user" or args['verify'] == "both":
                    user_test_passed = user_test.test()
            except TestError as e:
                logging.error(str(e))

        # Clean the lab at the end of the test.
        LcleanCommand().run(lab_path, [])

        if args['verify']:
            if not builtin_test_passed or not user_test_passed:
                sys.exit(1)
