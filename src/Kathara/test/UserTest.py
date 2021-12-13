import difflib
import logging
import os
from typing import Union, Dict, List, Optional

from deepdiff import DeepDiff

from .. import utils
from ..exceptions import MachineSignatureNotFoundError
from ..foundation.test.Test import Test
from ..manager.Kathara import Kathara
from ..model.Lab import Lab
from ..model.Machine import Machine
from ..setting.Setting import Setting


class UserTest(Test):
    def __init__(self, lab: Lab) -> None:
        Test.__init__(self, lab)

    def create_signature(self) -> None:
        for (machine_name, machine) in self.lab.machines.items():
            machine_test_file = self._copy_machine_test_file(machine)

            if machine_test_file:
                logging.info("Building `user` signature for device %s..." % machine_name)

                machine_state = self._run_machine_test_file(machine)

                # Write the signature into the proper file
                with open("%s/%s.user" % (self.signature_path, machine_name), 'w') as machine_signature_file:
                    machine_signature_file.write(machine_state)

    def test(self) -> bool:
        test_passed = True

        for (machine_name, machine) in self.lab.machines.items():
            machine_test_file = self._copy_machine_test_file(machine)

            if machine_test_file:
                logging.info("Executing `user` tests for device %s..." % machine_name)

                machine_state = self._run_machine_test_file(machine)

                # Read the signature from machine file
                machine_signature_path = "%s/%s.user" % (self.signature_path, machine.name)
                if os.path.exists(machine_signature_path):
                    with open(machine_signature_path, 'r') as machine_signature_file:
                        machine_signature = machine_signature_file.read()
                else:
                    raise MachineSignatureNotFoundError("Signature for device `%s` not found! Exiting..." %
                                                        machine_name
                                                        )

                # Save machine state into result file
                machine_result_path = "%s/%s.user" % (self.results_path, machine.name)
                with open(machine_result_path, 'w') as machine_result_file:
                    machine_result_file.write(machine_state)

                diff = self.check_signature(machine_signature, machine_state)
                test_passed = False if diff else test_passed

                machine_diff_path = "%s/%s.diff" % (self.results_path, machine.name)
                with open(machine_diff_path, 'a') as machine_diff_file:
                    machine_diff_file.write(utils.format_headers("User Test Result") + '\n')
                    machine_diff_file.write("\n".join(diff) + "\n" if diff else "OK\n")
                    machine_diff_file.write(utils.format_headers() + "\n\n")

        return test_passed

    def check_signature(self, signature: Union[Dict, str], status: Union[Dict, str]) -> Union[DeepDiff, List]:
        signature = signature.splitlines()
        status = status.splitlines()

        # Do the diff between the arrays, n=0 removes context strings
        diff = difflib.unified_diff(signature, status, n=0, lineterm="")
        # Remove headers of the diff from the result
        return [x for x in filter(lambda x: not x.startswith(('---', '+++', '@@')), diff)]

    def _copy_machine_test_file(self, machine: Machine) -> Optional[str]:
        machine_test_file = os.path.join(self.test_path, "%s.test" % machine.name)

        if os.path.exists(machine_test_file):
            Kathara.get_instance().copy_files(machine, {"/%s.test" % machine.name: machine_test_file})

            return machine_test_file
        else:
            return None

    @staticmethod
    def _run_machine_test_file(machine: Machine) -> str:
        # Give execution permissions to test file
        Test._get_machine_command_output(lab_hash=machine.lab.hash,
                                         machine_name=machine.name,
                                         command="chmod u+x /%s.test" % machine.name
                                         )

        # Run the test file inside the container
        (stdout, stderr) = Test._get_machine_command_output(lab_hash=machine.lab.hash,
                                                            machine_name=machine.name,
                                                            command="%s -c /%s.test" % (
                                                                Setting.get_instance().device_shell,
                                                                machine.name
                                                            ))

        return stdout if stdout else stderr if stderr else ""
