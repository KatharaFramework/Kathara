import argparse
import logging
import os
import shutil
import time

from .LcleanCommand import LcleanCommand
from .LstartCommand import LstartCommand
from .. import utils
from ..exceptions import TestError
from ..foundation.command.Command import Command
from ..strings import strings, wiki_description
from ..test.BuiltinTest import BuiltInTest
from ..test.UserTest import UserTest


class LtestCommand(Command):
    __slots__ = ['parser']

    def __init__(self):
        Command.__init__(self)

        parser = argparse.ArgumentParser(
            prog='kathara ltest',
            description=strings['ltest'],
            epilog=wiki_description,
            add_help=False
        )

        parser.add_argument(
            '-h', '--help',
            action='help',
            default=argparse.SUPPRESS,
            help='Show an help message and exit.'
        )

        parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the lab.'
        )
        parser.add_argument(
            '-R', '--rebuild-signature',
            dest="rebuild_signature",
            required=False,
            action='store_true',
            help='Force generating a new signature for the lab, even if one already exists. '
                 'Overwrites any existing signature.'
        )
        parser.add_argument(
            '-s', '--sleep',
            required=False,
            help='Minutes to wait from lab startup before running the tests.'
        )
        parser.add_argument(
            '--verify',
            required=False,
            choices=['builtin', 'user', 'both'],
            help='Compares current lab state with stored signature.'
        )

        self.parser = parser

    def run(self, current_path, argv):
        args = self.parser.parse_args(argv)

        lab_path = args.directory.replace('"', '').replace("'", '') if args.directory else current_path
        lab_path = utils.get_absolute_path(lab_path)

        # Tests run without terminals, no shared and /hosthome dirs.
        new_argv = ["--noterminals", "--no-shared", "--no-hosthome"]

        # Start the lab
        lab = LstartCommand().run(lab_path, new_argv)

        if args.sleep:
            try:
                sleep_minutes = int(args.sleep)
                if sleep_minutes < 0:
                    raise ValueError()

                logging.info("Waiting %s minutes before running tests..." % sleep_minutes)
                time.sleep(sleep_minutes * 60)
            except ValueError:
                raise ValueError("--sleep value is not valid!")

        # Run Tests and store in signature
        builtin_test = BuiltInTest(lab)
        user_test = UserTest(lab)

        if not args.verify:
            signature_test_path = os.path.join(lab.path, "_test", "signature")

            if not os.path.exists(signature_test_path) or args.rebuild_signature:
                shutil.rmtree(signature_test_path, ignore_errors=True)
                os.makedirs(signature_test_path, exist_ok=True)

                builtin_test.create_signature()
                user_test.create_signature()
            else:
                logging.error("Signature for current lab already exists. Exiting...")
        else:
            result_test_path = os.path.join(lab.path, "_test", "results")

            shutil.rmtree(result_test_path, ignore_errors=True)
            os.makedirs(result_test_path, exist_ok=True)

            try:
                if args.verify == "builtin" or args.verify == "both":
                    builtin_test.test()
                if args.verify == "user" or args.verify == "both":
                    user_test.test()
            except TestError as e:
                logging.error(str(e))

        # Clean the lab at the end of the test.
        LcleanCommand().run(lab_path, [])
