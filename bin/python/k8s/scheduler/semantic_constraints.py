import os
import re
import sys
from multiprocessing.pool import ThreadPool

supported_suites = ["zebra", "quagga", "frr"]
supported_protocols = ["bgpd", "ospfd"]


def parse_bgpd_config(config_path):
    with open(config_path, "r") as bgpd_file:
        matches = re.findall("router bgp (\d+)", bgpd_file.read())
        return matches


def parse_ospfd_config(config_path):
    with open(config_path, "r") as ospfd_file:
        matches = re.findall("network .*? area (.*)", ospfd_file.read())
        return matches


def read_and_parse_configuration_file(protocol, protocol_config):
    protocol_function = getattr(sys.modules[__name__], 'parse_%s_config' % protocol)
    return protocol_function(protocol_config)


def search_machine_configurations(lab_path):
    # Get all folders in lab path
    folder_list = os.listdir(lab_path)

    protocols_info = {k: {} for k in supported_protocols}

    # Create a thread pool (which will be used to parse config files concurrently)
    thread_pool = ThreadPool()

    # Scan folder files
    for folder_file in folder_list:
        machine_name = folder_file
        folder_file = os.path.join(lab_path, folder_file)

        # Only enter in subdirectories (machine configuration)
        if os.path.isdir(folder_file):
            # Check if at least one suite directory is present
            for suite in supported_suites:
                suite_path = os.path.join(folder_file, "etc/%s" % suite)

                if os.path.isdir(suite_path):
                    async_results = {}

                    # Check if this machine has supported protocols file
                    for protocol in supported_protocols:
                        protocol_config = os.path.join(suite_path, "%s.conf" % protocol)

                        # If protocol configuration file is found, get relevant info
                        if os.path.isfile(protocol_config):
                            async_results[protocol] = thread_pool.apply_async(read_and_parse_configuration_file,
                                                                              args=(protocol, protocol_config)
                                                                              )

                    for protocol in async_results:
                        for info in async_results[protocol].get():
                            protocols_info[protocol][machine_name] = info

                    break

    return protocols_info


def enhance_distances(adjacency_matrix, label_to_idx, protocol_info):
    # Gets a set of protocol values used in the dict.
    protocol_values = set(protocol_info.values())

    for protocol_value in protocol_values:
        # Gets only the list of machines with a particular protocol value
        protocol_value_machines = [k for k in protocol_info if protocol_info[k] == protocol_value]

        # Gets all the other machines (with different protocol value)
        other_machines = [k for k in protocol_info if protocol_info[k] != protocol_value]

        # Scan each machine with the same protocol value
        for machine_name in protocol_value_machines:
            # Scan other machines with same protocol value, skipping the current from the outer loop
            for other_machine_name in protocol_value_machines:
                if machine_name != other_machine_name:
                    machine_idx = label_to_idx[machine_name]
                    other_machine_idx = label_to_idx[other_machine_name]

                    # Enhance the distance of those machines, multiplying their distance with a factor of 0.75
                    adjacency_matrix[machine_idx, other_machine_idx] *= 0.75

            # Scan through the machines with a different protocol value
            for other_machine_name in other_machines:
                machine_idx = label_to_idx[machine_name]
                other_machine_idx = label_to_idx[other_machine_name]

                # Boost the distance between the currently scanned machine and the machines with other protocol values
                adjacency_matrix[machine_idx, other_machine_idx] *= 3.75


def get_neighbours(adjacency_matrix, label_to_idx, machine_name):
    machine_idx = label_to_idx[machine_name]
    machine_column = adjacency_matrix[:, machine_idx]

    idx_to_label = {v: k for k, v in label_to_idx.iteritems()}
    return [idx_to_label[i] for i, val in enumerate(machine_column) if val > 0]


# Simple BFS that stops when a neighbor has the desired protocol info
def get_protocol_info_from_neighbours(protocol_info, adjacency_matrix, label_to_idx, start):
    queue = [start]
    visited = []

    while queue:
        graph_vertex = queue.pop(0)

        neighbors = get_neighbours(adjacency_matrix, label_to_idx, graph_vertex)

        for neighbor in neighbors:
            if neighbor not in visited:
                if neighbor in protocol_info:
                    return protocol_info[neighbor]

                queue.append(neighbor)
                visited.append(neighbor)

    return None


def infer_protocol_info(protocol_info, adjacency_matrix, label_to_idx):
    # Scan the lab machines
    for machine_name in label_to_idx:
        # If a machine haven't the protocol info, search in its neighbours and assign it.
        if machine_name not in protocol_info:
            neighbour_info = get_protocol_info_from_neighbours(protocol_info,
                                                               adjacency_matrix,
                                                               label_to_idx,
                                                               machine_name
                                                               )

            if neighbour_info is not None:
                protocol_info[machine_name] = neighbour_info


def add_semantic_constraints(adjacency_matrix, label_to_idx, path):
    protocols_info = search_machine_configurations(path)

    for supported_protocol in supported_protocols:
        if len(protocols_info[supported_protocol]) > 0:
            infer_protocol_info(protocols_info[supported_protocol], adjacency_matrix, label_to_idx)
            enhance_distances(adjacency_matrix, label_to_idx, protocols_info[supported_protocol])
