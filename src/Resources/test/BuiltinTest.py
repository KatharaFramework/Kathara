import json
import logging

from deepdiff import DeepDiff

import os
from .. import utils
from ..exceptions import MachineSignatureNotFoundError
from ..foundation.test.Test import Test
from ..manager.ManagerProxy import ManagerProxy


class BuiltInTest(Test):
    def __init__(self, lab):
        Test.__init__(self, lab)

    def create_signature(self):
        for (machine_name, machine) in self.lab.machines.items():
            logging.info("Building `builtin` signature for machine %s..." % machine_name)

            machine_status = self._get_machine_status(machine)

            # Write the signature into the proper file
            with open("%s/%s.builtin" % (self.signature_path, machine_name), 'w') as machine_signature_file:
                machine_signature_file.write(json.dumps(machine_status, indent=4))

    def test(self):
        test_passed = True

        for (machine_name, machine) in self.lab.machines.items():
            logging.info("Executing `builtin` tests for machine %s..." % machine_name)

            machine_state = self._get_machine_status(machine)

            # Read the signature from machine file
            machine_signature_path = "%s/%s.builtin" % (self.signature_path, machine.name)
            if os.path.exists(machine_signature_path):
                with open(machine_signature_path, 'r') as machine_signature_file:
                    machine_signature = json.loads(machine_signature_file.read())
            else:
                raise MachineSignatureNotFoundError("Signature for machine `%s` not found! Exiting..." % machine_name)

            # Save machine state into result file
            machine_result_path = "%s/%s.builtin" % (self.results_path, machine.name)
            with open(machine_result_path, 'w') as machine_result_file:
                machine_result_file.write(json.dumps(machine_state, indent=4))

            diff = self.check_signature(machine_signature, machine_state)
            test_passed = False if diff else test_passed

            machine_diff_path = "%s/%s.diff" % (self.results_path, machine.name)
            with open(machine_diff_path, 'w') as machine_diff_file:
                machine_diff_file.write(utils.format_headers("Builtin Test Result") + '\n')
                machine_diff_file.write(json.dumps(diff, indent=4) + "\n" if diff else "OK\n")
                machine_diff_file.write(utils.format_headers() + "\n\n")

        return test_passed

    def check_signature(self, signature, status):
        diff = DeepDiff(status, signature, ignore_order=True)

        if "iterable_item_added" in diff:
            diff["it_is"] = diff.pop("iterable_item_added")
        if "iterable_item_removed" in diff:
            diff["should_be"] = diff.pop("iterable_item_removed")

        return diff

    @staticmethod
    def _get_machine_status(machine):
        # Machine interfaces
        (ip_addr, _) = json.loads(ManagerProxy.get_instance().exec(machine_name=machine,
                                                                   command="ip -j addr show"
                                                                   )
                                  )

        # Get only relevant information (interface name, state and list of address/prefix)
        ip_addr_clean = {}
        for info in ip_addr:
            ip_addr_clean[info['ifname']] = {'ip_addresses': [x["local"] + "/" + str(x["prefixlen"])
                                                              for x in info["addr_info"]
                                                              ],
                                             'state': info['operstate']
                                             }

        # Machine routes
        (ip_route, _) = json.loads(ManagerProxy.get_instance().exec(machine_name=machine,
                                                                    command="ip -j route show"
                                                                    )
                                   )

        # Machine opened ports
        (net_stat, _) = ManagerProxy.get_instance().exec(machine_name=machine,
                                                         command="netstat -tuwln"
                                                         )
        # Remove Docker ports and header lines. Sort the array alphabetically.
        net_stat = sorted([filter(lambda x: "127.0.0.11" not in x, net_stat.splitlines())][2:])

        # Machine processes
        (processes, _) = ManagerProxy.get_instance().exec(machine_name=machine,
                                                          command="ps -e -o command"
                                                          )
        # Remove header line and sort the array alphabetically.
        processes = sorted([x.strip() for x in processes.splitlines()[1:]])

        return {
            "interfaces": ip_addr_clean,
            "route": ip_route,
            "listening_ports": net_stat,
            "processes": processes
        }
