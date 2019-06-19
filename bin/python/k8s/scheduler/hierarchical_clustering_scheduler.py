import scheduler_utils


inf = float('inf')


def min_distance(distances):
    current_min_start_element = ()
    current_min_end_element = ()
    current_min_distance = inf

    # Loop on element distances
    for start_element in distances:
        # Dict containing all the elements with their distance of start_element
        all_distances_from_element = distances[start_element]

        # Loop on those distances
        for end_element in all_distances_from_element:
            # Take distance value
            distance = all_distances_from_element[end_element]

            # Check if the distance is less or equal the the current min
            # Equal is needed to do alpha checks
            if distance <= current_min_distance:
                # Only check alpha if this is not the first iteration
                if current_min_distance != inf:
                    # Even if the new value is lesser than current min, updates should only happen if is convenient
                    # to merge two clusters of smaller size instead of clusters of bigger size
                    # Ex. current min: (A, B, C) - (F, E) - distance = 1
                    #     new min: (D) (H) - distance = 1
                    # Better to take the new value as current min
                    if len(start_element) > len(current_min_start_element) or \
                       len(start_element) > len(current_min_end_element) or \
                       len(end_element) > len(current_min_start_element) or \
                       len(end_element) > len(current_min_end_element):
                        continue

                    # If previous condition is met.
                    # Check if the new distance is equal, if so, don't update (it's useless)
                    if distance == current_min_distance:
                        continue

                # If all previous conditions are met, update values
                current_min_distance = distance
                current_min_start_element = start_element
                current_min_end_element = end_element

    return (current_min_start_element, current_min_end_element), current_min_distance


def merge_distances(first, second, distances):
    # Get distances of first element from the others
    distances_first = distances[first]
    # Get distances of second element from the others
    distances_second = distances[second]

    # Create a new tuple key to add to the dict
    tuple_key = first + second
    distances[tuple_key] = {}

    # Loop on the elements
    for element in distances_first:
        # Ignore current elements to merge
        if element != first and element != second:
            # Calculate the distance of the new element from the others
            # To do so, to an average of the distance of the first element from the others and the distance
            # of the second element from the others
            avg_value = (distances_first[element] + distances_second[element]) / 2.

            # Update values in both new tuple added and other element dict
            distances[tuple_key][element] = avg_value
            distances[element][tuple_key] = avg_value

            del distances[element][first]
            del distances[element][second]

    # Delete old keys from the dict (those are now merged)
    del distances[first]
    del distances[second]

    return distances


def hierarchical_clustering(x, distances, desired_cluster_size):
    # In the beginning, assign each element to a different cluster
    clusters = [(el, ) for el in x]

    # Clone distances dict just to not touch the parameter value
    new_distances = distances.copy()

    # This condition will halt the split if we're reached the desired split size
    while len(desired_cluster_size) < len(clusters) > 1:
        # Search for the element couple with minimum distance
        (start, end), min_value = min_distance(new_distances)
        # Create a new cluster tuple
        new_cluster = start + end

        # Update cluster list with new created clusters
        clusters.remove(start)
        clusters.remove(end)
        clusters.append(new_cluster)

        # Update distances array, adding distances of the other clusters from the new one
        new_distances = merge_distances(start, end, new_distances)

    return clusters


def get_constraints_for_lab(machines):
    return scheduler_utils.calculate_constraints(machines, hierarchical_clustering)
