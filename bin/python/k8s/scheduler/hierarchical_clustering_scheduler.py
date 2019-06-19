import scheduler_utils


inf = float('inf')


def min_distance(distances):
    current_min_start_vertex = ()
    current_min_end_vertex = ()
    current_min_value = inf

    for start_vertex in distances:
        all_distances_from_vertex = distances[start_vertex]

        for end_vertex in all_distances_from_vertex:
            value = all_distances_from_vertex[end_vertex]

            if value <= current_min_value:
                if current_min_value != inf:
                    if len(start_vertex) > len(current_min_start_vertex) \
                       or len(start_vertex) > len(current_min_end_vertex) \
                       or len(end_vertex) > len(current_min_start_vertex) \
                       or len(end_vertex) > len(current_min_end_vertex):
                        continue

                    if value == current_min_value:
                        continue

                current_min_value = value
                current_min_start_vertex = start_vertex
                current_min_end_vertex = end_vertex

    return (current_min_start_vertex, current_min_end_vertex), current_min_value


def merge_distances(first, second, distances):
    distances_first = distances[first]
    distances_second = distances[second]

    tuple_key = first + second

    distances[tuple_key] = {}
    for graph_vertex in distances_first:
        if graph_vertex != first and graph_vertex != second:
            min_value = (distances_first[graph_vertex] + distances_second[graph_vertex]) / 2.

            distances[tuple_key][graph_vertex] = min_value
            distances[graph_vertex][tuple_key] = min_value

            del distances[graph_vertex][first]
            del distances[graph_vertex][second]

    del distances[first]
    del distances[second]

    return distances


def hierarchical_clustering(x, distances, available_nodes):
    clusters = [(el, ) for el in x]

    new_distances = distances.copy()

    # This will halt the split if we're reached the desired split size.
    while len(available_nodes) < len(clusters) > 1:
        (start, end), min_value = min_distance(new_distances)
        new_cluster = start + end

        clusters.remove(start)
        clusters.remove(end)
        clusters.append(new_cluster)

        new_distances = merge_distances(start, end, new_distances)

    return clusters


def get_constraints_for_lab(machines):
    return scheduler_utils.calculate_constraints(machines, hierarchical_clustering)
