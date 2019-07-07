import netkit_commons as nc
from kubernetes.client.apis import core_v1_api
import semantic_constraints
from scipy.sparse import csr_matrix


inf = float('inf')


def convert_machines_to_adjacency_matrix(machines):
    machines = {machine_name: [v1 for (v1, v2) in machines[machine_name]] for machine_name in machines}

    label_to_idx = {name: i for i, name in enumerate(machines.keys())}
    rows, cols, data = [], [], []

    for idx, machine_name in enumerate(machines):
        # With this trick we only get the link names
        links = machines[machine_name]

        # Check other machines, looping on the same dict
        # Since matrix is symmetric, the loop is started from the element next to the current one
        # Because it's useless to check it from the beginning
        for other_machine_name in machines.keys()[(idx + 1):]:
            start_idx = label_to_idx[machine_name]
            end_idx = label_to_idx[other_machine_name]

            # Get a list with only link names
            other_links = machines[other_machine_name]

            # If there's a link between the machines, add it in the adjacency matrix
            # The edge weight is 1 in the beginning.
            if set(links).intersection(other_links):
                rows.append(start_idx)
                cols.append(end_idx)
                data.append(1)

                rows.append(end_idx)
                cols.append(start_idx)
                data.append(1)

    matrix_size = len(machines)
    # Create sparse adjacency matrix
    adjacency_matrix = csr_matrix((data, (rows, cols)), shape=(matrix_size, matrix_size), dtype=float)
    adjacency_matrix = adjacency_matrix.tolil()

    return adjacency_matrix, label_to_idx


def get_available_nodes():
    # # Get k8s current available nodes
    # core_api = core_v1_api.CoreV1Api()
    # # Get node list (API Response), a purge is needed
    # api_nodes = core_api.list_node()
    #
    # # Purge the API response
    # # Get only node names of nodes which aren't masters
    # available_nodes = [node.metadata.name for node in api_nodes.items
    #                    if [x.status for x in node.status.conditions if x.type == "Ready"].pop() == "True" and
    #                    "node-role.kubernetes.io/master" not in node.metadata.labels
    #                    ]

    available_nodes = []
    for i in range(1, 51, 1):
        available_nodes.append("kubeslave" + str(i))

    # available_nodes = ["kubeslave1", "kubeslave2"]

    return available_nodes


def convert_cluster_to_node_selectors(available_nodes, split_cluster):
    node_selectors = {}

    # Loop on the split list
    for idx, cluster_machines in enumerate(split_cluster):
        # Create a new element in the dict for each machine in this cluster tuple and assign it
        # to the node with the index idx
        for machine_name in cluster_machines:
            node_selectors[machine_name] = available_nodes[idx]

    return node_selectors


def calculate_constraints(machines, scheduling_function, lab_path, use_semantic):
    # if nc.PRINT:
    #     print "Print mode, scheduler is not run."
    #     return None

    available_nodes = get_available_nodes()

    # Skip clustering algorithm if there's only one node
    if len(available_nodes) <= 1:
        return None

    adjacency_matrix, label_to_idx = convert_machines_to_adjacency_matrix(machines)

    if use_semantic:
        semantic_constraints.add_semantic_constraints(adjacency_matrix, label_to_idx, lab_path)

    machine_clusters = scheduling_function(adjacency_matrix, label_to_idx, available_nodes)

    return convert_cluster_to_node_selectors(available_nodes, machine_clusters)
