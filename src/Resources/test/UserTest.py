import difflib
import logging
import tarfile

import os
from .. import utils
from ..exceptions import MachineSignatureNotFoundError
from ..foundation.test.Test import Test
from ..manager.ManagerProxy import ManagerProxy
from ..setting.Setting import Setting


class UserTest(Test):
    def __init__(self, lab):
        Test.__init__(self, lab)

    def create_signature(self):
        for (machine_name, machine) in self.lab.machines.items():
            machine_test_file = self._copy_machine_test_file(machine)

            if machine_test_file:
                logging.info("Building `user` signature for device %s..." % machine_name)

                machine_state = self._run_machine_test_file(machine)

                # Write the signature into the proper file
                with open("%s/%s.user" % (self.signature_path, machine_name), 'w') as machine_signature_file:
                    machine_signature_file.write(machine_state)

    def test(self):
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

    def check_signature(self, signature, status):
        signature = signature.splitlines()
        status = status.splitlines()

        # Do the diff between the arrays, n=0 removes context strings
        diff = difflib.unified_diff(signature, status, n=0, lineterm="")
        # Remove headers of the diff from the result
        return [x for x in filter(lambda x: not x.startswith(('---', '+++', '@@')), diff)]

    def _copy_machine_test_file(self, machine):
        machine_test_file = os.path.join(self.test_path, "%s.test" % machine.name)

        if os.path.exists(machine_test_file):
            tar_data = self._pack_machine_test_file(machine.name, machine_test_file)

            ManagerProxy.get_instance().copy_files(machine, "/", tar_data)

            return machine_test_file
        else:
            return None

    def _pack_machine_test_file(self, machine_name, machine_test_file):
        tar_path = "%s/test_file.tar.gz" % self.test_path

        with tarfile.open(tar_path, "w:gz") as tar:
            (tarinfo, content) = utils.pack_file_for_tar(machine_test_file,
                                                         "/%s.test" % machine_name
                                                         )
            tar.addfile(tarinfo, content)

        with open(tar_path, "rb") as tar_file:
            tar_data = tar_file.read()

        os.remove(tar_path)

        return tar_data

    @staticmethod
    def _run_machine_test_file(machine):
        # Give execution permissions to test file
        ManagerProxy.get_instance().exec(lab_hash=machine.lab.folder_hash,
                                         machine_name=machine.name,
                                         command="chmod u+x /%s.test" % machine.name
                                         )

        # Run the test file inside the container
        (result_stdout, _) = ManagerProxy.get_instance().exec(lab_hash=machine.lab.folder_hash,
                                                              machine_name=machine.name,
                                                              command="%s -c /%s.test" % (
                                                                  Setting.get_instance().device_shell,
                                                                  machine.name
                                                              ))

        return result_stdout
