from sklearn.cluster import SpectralClustering

import scheduler_utils


def spectral_clustering(adjacency_matrix, label_to_idx, available_nodes):
    k = len(available_nodes)

    # If number of nodes is greater than the machines number, assign each machine to a different node
    if k >= adjacency_matrix.shape[0]:
        return [(machine_name, ) for machine_name in label_to_idx]

    # Create the spectral clustering model, the `affinity` parameter is `precomputed` because the input matrix
    # is already a similarity matrix. `n_init` is the number of iterations of the K-Means algorithm.
    spectral_clustering_model = SpectralClustering(k, affinity='precomputed', n_init=1000)
    spectral_clustering_model.fit(adjacency_matrix)

    idx_to_label = {v: k for k, v in label_to_idx.iteritems()}

    # Assign each machine to a cluster. The result of the spectral clustering is a numeric-indexed array of labels,
    # then the machine corresponding to a specific index is put into the cluster (identified by a label).
    return [tuple([idx_to_label[idx] for idx, val in enumerate(spectral_clustering_model.labels_) if val == i])
            for i in range(0, k, 1)]


def get_constraints_for_lab(machines, lab_path, use_semantic=False):
    return scheduler_utils.calculate_constraints(machines,
                                                 spectral_clustering,
                                                 lab_path=lab_path,
                                                 use_semantic=use_semantic
                                                 )
