import numpy as np
from kneed import KneeLocator
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

from scanner.Detection.ClusteringBased.Clustering.ClusteringUtil import preprocess_data


class DBSCANClustering:
    def cluster(self,
                data,
                distance_type: str = 'tlsh',
                dbscan_additional_metric = None,
                eps='sil',
                min_samples: int = 1,
                field_for_index: str = '_id',
                field_for_distance: str = 'hash'):

        clustering_metric, preprocessed_data = preprocess_data(data=data,
                                                               distance_type=distance_type,
                                                               dbscan_additional_metric=dbscan_additional_metric,
                                                               field_for_index=field_for_index,
                                                               field_for_distance=field_for_distance)

        # Different methods for optimal cluster count detection
        if eps == 'kneed_lib':
            optimal_eps = self._optimal_eps_kneedlib(preprocessed_data, clustering_metric)
        elif eps == 'knee':
            optimal_eps = self._optimal_eps_knee(preprocessed_data, clustering_metric)
        elif eps == 'sil':
            optimal_eps = self._optimal_eps_silhouette_score(preprocessed_data, clustering_metric, min_samples)
        elif eps == 'infinitesimal-fixed':
            optimal_eps = 10**(-9)
        else:
            optimal_eps = eps

        db = DBSCAN(eps=optimal_eps, min_samples=min_samples, metric=clustering_metric).fit(preprocessed_data)

        labels = db.labels_

        # Number of clusters
        n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

        return n_clusters_, labels

    def _optimal_eps_silhouette_score(self, data, metric, min_samples):
        sil = []
        eps_data = []
        n_samples = data.shape[0]

        # Idea: We start increasing the epsilon stepwise from 0.1 till 1 and check the silhouette score
        # The distance matrix is scaled so the distances are between 0 and 1
        # This means that the optimal eps should also be between 0 and 1
        # We select the eps for which the highest silhouette score was calculated
        # Note: The calculation can more granular. For testing purposes the step was selected as 0.1
        for multiplier in range(2, 10):
            calc_eps = 0.1 * multiplier
            db = DBSCAN(eps=calc_eps, min_samples=min_samples, metric=metric).fit(data)
            labels = db.labels_
            unique_labels = set(labels)

            if len(unique_labels) > 1 and n_samples > len(labels):
                sil_score = silhouette_score(data, labels, metric=metric)
            else:
                sil_score = 0

            sil.append(sil_score)
            eps_data.append(calc_eps)

        eps_optimal = eps_data[np.argmax(sil)]
        return eps_optimal

    def _optimal_eps_knee(self, data, metric):
        if data.shape == (1, 1):
            return 0.01

        nearest_neighbors = NearestNeighbors(n_neighbors=2, metric=metric)
        neighbors = nearest_neighbors.fit(data)
        distances, indices = neighbors.kneighbors(data)
        distances = np.sort(distances[:, 1], axis=0)

        if len(distances) < 2:
            return 0.01

        distinct_distances, distinct_distances_counts = np.unique(distances, return_counts=True)
        is_polynomial = len(distinct_distances_counts) > 1

        if is_polynomial:
            distances_diff = np.diff(distances)
            max_idx = np.argmax(distances_diff)
            eps = distances[max_idx + 1]
            eps = eps - 0.0001
        else:
            eps = distances[0]
            if eps == 0:
                eps = 0.0001
            else:
                eps = eps - 0.0001

        return eps

    def _optimal_eps_kneedlib(self, data, metric, S=1):
        if data.shape == (1, 1):
            return 0.01

        nearest_neighbors = NearestNeighbors(n_neighbors=2, metric=metric)
        neighbors = nearest_neighbors.fit(data)
        distances, indices = neighbors.kneighbors(data)
        distances = np.sort(distances[:, 1], axis=0)

        # Remove zeros, because they cause to sudden change and appear quite often in the dataset
        # This make eps stay at 0
        distances = distances[distances != 0]

        if len(distances) < 2:
            return 0.01

        distinct_distances, distinct_distances_counts = np.unique(distances, return_counts=True)

        is_polynomial = len(distinct_distances_counts) > 1

        if is_polynomial:
            i = range(len(distances))
            knee = KneeLocator(i, distances, S=S, curve='convex', interp_method="polynomial")

            # If no knee is found, take the first distance for eps
            if knee.knee is None:
                eps = distances[0]
            else:
                eps = distances[knee.knee]
        else:
            eps = distances[0] - 0.01

        return eps
