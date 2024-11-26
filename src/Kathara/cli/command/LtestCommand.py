import argparse
import logging
import os
import shutil
import time
from typing import List

from .LcleanCommand import LcleanCommand
from .LstartCommand import LstartCommand
from ... import utils
from ...exceptions import TestError
from ...foundation.cli.command.Command import Command
from ...manager.Kathara import Kathara
from ...model.Lab import Lab
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
            help='Show a help message and exit.'
        )

        self.parser.add_argument(
            '-d', '--directory',
            required=False,
            help='Specify the folder containing the network scenario.'
        )
        self.parser.add_argument(
            '-R', '--rebuild-signature',
            dest="rebuild_signature",
            required=False,
            action='store_true',
            help='Force generating a new signature for the network scenario, even if one already exists. '
                 'Overwrites any existing signature.'
        )
        self.parser.add_argument(
            '--wait',
            required=False,
            metavar='MINUTES',
            help='Minutes to wait from network scenario startup before running the tests (can be a decimal number).'
        )
        self.parser.add_argument(
            '--verify',
            required=False,
            choices=['builtin', 'user', 'both'],
            help='Compares current network scenario state with stored signature.'
        )

    def run(self, current_path: str, argv: List[str]) -> int:
        logging.warning(
            "The `ltest` command is deprecated and will be removed in the next release. "
            "Please use the `kathara-lab-checker` tool as its replacement with enhanced functionalities."
        )
        logging.warning("For further information, visit: https://github.com/KatharaFramework/kathara-lab-checker")

        self.parse_args(argv)
        args = self.get_args()

        lab_path = args['directory'].replace('"', '').replace("'", '') if args['directory'] else current_path
        lab_path = utils.get_absolute_path(lab_path)

        signature_test_path = None
        if not args['verify']:
            signature_test_path = os.path.join(lab_path, "_test", "signature")

            if os.path.exists(signature_test_path) and not args['rebuild_signature']:
                self.console.print(
                    f"[bold red]\u00d7 Signature for current network scenario already exists."
                )
                return 1

        # Tests run without terminals, no shared and /hosthome dirs.
        new_argv = ["--noterminals", "--no-shared", "--no-hosthome"]

        # Start the lab
        LstartCommand().run(lab_path, new_argv)
        lab = Lab(name=None, path=lab_path)
        Kathara.get_instance().update_lab_from_api(lab)

        if args['wait']:
            try:
                sleep_minutes = float(args['wait'])
                if sleep_minutes < 0:
                    raise ValueError("--wait value must be greater than zero!")

                with self.console.status(
                        f"Waiting {sleep_minutes} minutes before running tests...",
                        spinner="dots"
                ) as _:
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
            result_test_path = os.path.join(lab.fs_path(), "_test", "results")

            shutil.rmtree(result_test_path, ignore_errors=True)
            os.makedirs(result_test_path, exist_ok=True)

            try:
                if args['verify'] == "builtin" or args['verify'] == "both":
                    builtin_test_passed = builtin_test.test()
                if args['verify'] == "user" or args['verify'] == "both":
                    user_test_passed = user_test.test()
            except TestError as e:
                self.console.print(f"[bold red]\u00d7 Tests failed: {str(e)}")

        # Clean the lab at the end of the test.
        LcleanCommand().run(lab_path, [])

        if args['verify']:
            if not builtin_test_passed or not user_test_passed:
                return 1

        return 0
