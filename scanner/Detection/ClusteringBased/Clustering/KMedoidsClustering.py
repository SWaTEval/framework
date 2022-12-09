import numpy as np
from sklearn_extra.cluster import KMedoids
from sklearn.metrics import silhouette_score

from scanner.Detection.ClusteringBased.Clustering.ClusteringUtil import preprocess_data
from scanner.Utilities.Util import generate_hash2vec_dataset, extract_hashes
from scanner.Utilities.Distance import Distance


class KMedoidsClustering:

    def cluster(self,
                data,
                distance_type: str = 'tlsh',
                field_for_index: str = '_id',
                field_for_distance: str = 'hash'):

        clustering_metric, preprocessed_data = preprocess_data(data=data,
                                                               distance_type=distance_type,
                                                               field_for_index=field_for_index,
                                                               field_for_distance=field_for_distance,
                                                               dbscan_additional_metric=None)

        max_clusters = preprocessed_data.shape[0]

        if max_clusters > 30:
            max_clusters = int(max_clusters / 2)

        sil = []
        cluster_counts = []

        for n_clusters in range(1, max_clusters):
            kmedoids = KMedoids(n_clusters=n_clusters, metric=clustering_metric).fit(preprocessed_data)
            labels = kmedoids.labels_

            uniquie_labels = np.unique(np.asarray(labels))
            if len(uniquie_labels) > 1:
                sil_score = silhouette_score(preprocessed_data, labels, metric=clustering_metric)
            else:
                sil_score = 0

            sil.append(sil_score)
            cluster_counts.append(n_clusters)

        if len(sil) > 0:
            optimal_clusters = np.argmax(sil) + 1  # We add one, because the argmax returns zero based index
            kmedoids = KMedoids(n_clusters=optimal_clusters, metric=clustering_metric).fit(preprocessed_data)
            labels = kmedoids.labels_.tolist()
        else:
            labels = [0]

        # Number of clusters
        n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

        return n_clusters_, labels
