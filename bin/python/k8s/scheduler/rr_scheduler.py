import scheduler_utils


def round_robin(adjacency_matrix, label_to_idx, available_nodes):
    k = len(available_nodes)
    clusters = [() for _ in range(0, k, 1)]

    i = 0
    for machine_name in label_to_idx.keys():
        clusters[i] += (machine_name, )

        i += 1
        if i % k == 0:
            i = 0

    return clusters


def get_constraints_for_lab(machines, lab_path, use_semantic=False):
    return scheduler_utils.calculate_constraints(machines,
                                                 round_robin,
                                                 lab_path=lab_path,
                                                 use_semantic=use_semantic
                                                 )
