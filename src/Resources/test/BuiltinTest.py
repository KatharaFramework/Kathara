import json
import logging
import os
from deepdiff import DeepDiff 

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
            with open("%s/%s.default" % (self.signature_path, machine_name), 'w') as machine_signature_file:
                machine_signature_file.write(json.dumps(machine_status, indent=True))

    def test(self):
        for (machine_name, machine) in self.lab.machines.items():
            logging.info("Executing `builtin` tests for machine %s..." % machine_name)

            machine_status = self._get_machine_status(machine)

            # Read the signature from machine file
            machine_signature_path = "%s/%s.default" % (self.signature_path, machine.name)
            if os.path.exists(machine_signature_path):
                with open(machine_signature_path, 'r') as machine_signature_file:
                    machine_signature = json.loads(machine_signature_file.read())
            else:
                raise MachineSignatureNotFoundError("Signature for machine `%s` not found! Exiting..." % machine_name)

            # Save machine state into result file
            machine_result_path = "%s/%s.default" % (self.results_path, machine.name)
            with open(machine_result_path, 'w') as machine_result_file:
                machine_result_file.write(json.dumps(machine_status, indent=True))

            # Check each signature element with the current status
            ddiff = DeepDiff(machine_signature, machine_status, ignore_order=True)

            machine_diff_path = "%s/%s.diff" % (self.results_path, machine.name)
            with open(machine_diff_path, 'w') as machine_diff_file:
                machine_diff_file.write(utils.format_headers("Builtin Test Result")+'\n')
                machine_diff_file.write(self._prettify_ddiff(ddiff) if ddiff else "OK\n")
                machine_diff_file.write("=============================================================\n\n")
            
    @staticmethod
    def _prettify_ddiff(ddiff):
        pretty_message = ""
        if ddiff['values_changed']:
            for k,value in ddiff['values_changed'].items():
                pretty_message += "%s is wrong: should it be %s but it is %s.\n" % (_read_tree(k), value['old_value'], value['new_value'])

        if ddiff['iterable_item_added']:
            for k,value in ddiff['iterable_item_added'].items():
                pretty_message += "%s is wrong: shouldn't appear %s.\n" % (_read_tree(k), value)

        if ddiff['iterable_item_removed']:
            for k,value in ddiff['iterable_item_removed'].items():
                pretty_message += "%s is wrong: should appear %s.\n" % (_read_tree(k), value)

        return pretty_message

    @staticmethod
    def _read_tree(path):
        # This method needs to understand something like "root['interfaces']['lo']['addr_info'][0]" or "root['route'][0]" and output
        # something like "The address of the interface lo" or "The route"
        return path

    @staticmethod
    def _get_machine_status(machine):
        # Machine interfaces
        ip_addr = json.loads(ManagerProxy.get_instance().exec(machine=machine,
                                                              command="ip -j addr show"
                                                              )
                             )

        # Get only relevant information (interface name, state and list of address/prefix)
        ip_addr_clean = {}
        for info in ip_addr:
            ip_addr_clean[info['ifname']] = {'addr_info' : [x["local"] + "/" + str(x["prefixlen"]) for x in info["addr_info"]],
                                           'operstate' : info['operstate']
                                           }

        # Machine routes
        ip_route = json.loads(ManagerProxy.get_instance().exec(machine=machine,
                                                               command="ip -j route show"
                                                               )
                              )

        # Machine opened ports
        net_stat = ManagerProxy.get_instance().exec(machine=machine,
                                                    command="netstat -tuwln"
                                                    )
        # Remove Docker ports and header lines. Sort the array alphabetically.
        net_stat = sorted([filter(lambda x: "127.0.0.11" not in x, net_stat.splitlines())][2:])

        # Machine processes
        processes = ManagerProxy.get_instance().exec(machine=machine,
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
