import netkit_commons as nc
from kubernetes.client.apis import core_v1_api

inf = float('inf')


def convert_machines_to_graph(machines):
    # Extract a dict with machine_name: [LINKS]
    machines = {machine_name: [k for (k, v) in machines[machine_name]] for machine_name in machines}

    graph_edges = []
    graph_vertices = machines.keys()

    for machine_name in machines:
        links = machines[machine_name]

        # Check other machines, looping on the same dict
        for other_machine_name in machines:
            # Skip current machine_name
            if other_machine_name != machine_name:
                other_links = machines[other_machine_name]

                # If there's a link between the machines, create a tuple representing an edge between the two nodes
                for link in links:
                    if link in other_links:
                        graph_edges.append((machine_name, other_machine_name))

    return graph_vertices, set(graph_edges)


def neighbours(graph_vertices, graph_edges):
    graph_neighbours = {graph_vertex: set() for graph_vertex in graph_vertices}

    # Convert the tuples in a dict with edge: [LIST OF NEIGHBORS]
    for (start, end) in graph_edges:
        graph_neighbours[start].add(end)

    return graph_neighbours


# Simple BFS visit with distance support
def get_vertex_distances(graph, start):
    queue = [start]
    distance_queue = [0]

    vertex_distances = {graph_vertex: inf for graph_vertex in graph.keys()}

    while queue:
        graph_vertex = queue.pop(0)
        current_distance = distance_queue.pop(0)
        vertex_distances[graph_vertex] = current_distance

        neighbors = graph[graph_vertex]

        for neighbor in neighbors:
            if vertex_distances[neighbor] == inf:
                vertex_distances[neighbor] = current_distance + 1
                queue.append(neighbor)
                distance_queue.append(current_distance + 1)

    # Edit the return value a bit, creating tuples (which are required by scheduling functions)
    return {(start,): {(k,): vertex_distances[k] for k in vertex_distances if k != start}}


def get_available_nodes():
    # Get k8s current available nodes
    core_api = core_v1_api.CoreV1Api()
    # Get node list (API Response), a purge is needed
    api_nodes = core_api.list_node()

    # Purge the API response
    # Get only node names of nodes which aren't masters
    available_nodes = [node.metadata.name for node in api_nodes.items
                       if [x.status for x in node.status.conditions if x.type == "Ready"].pop() == "True" and
                       "node-role.kubernetes.io/master" not in node.metadata.labels
                       ]

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


def calculate_constraints(machines, scheduling_function):
    if nc.PRINT:
        print "Print mode, scheduler is not run."
        return None

    available_nodes = get_available_nodes()

    # Skip clustering algorithm if there's only one node
    if len(available_nodes) <= 1:
        return None

    (vertices, edges) = convert_machines_to_graph(machines)

    adj_matrix = neighbours(vertices, edges)

    all_distances = {}
    for vertex in vertices:
        all_distances.update(get_vertex_distances(adj_matrix, vertex))

    split_cluster = scheduling_function(vertices, all_distances, available_nodes)

    return convert_cluster_to_node_selectors(available_nodes, split_cluster)
