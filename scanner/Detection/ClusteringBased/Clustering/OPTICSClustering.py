from sklearn.cluster import OPTICS

from scanner.Detection.ClusteringBased.Clustering.ClusteringUtil import preprocess_data
from scanner.Utilities.Util import generate_hash2vec_dataset, extract_hashes
from scanner.Utilities.Distance import Distance


class OPTICSClustering:

    def cluster(self,
                data,
                distance_type: str = 'tlsh',
                min_sample: int = 2,
                field_for_index: str = '_ind',
                field_for_distance: str = 'hash'):

        clustering_metric, preprocessed_data = preprocess_data(data=data,
                                                               distance_type=distance_type,
                                                               field_for_index=field_for_index,
                                                               field_for_distance=field_for_distance,
                                                               dbscan_additional_metric=None)

        if preprocessed_data.shape == (1, 1):
            return 0, [-1]

        optics = OPTICS(min_samples=min_sample, metric=clustering_metric).fit(preprocessed_data)
        labels = optics.labels_

        # Number of clusters
        n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

        return n_clusters_, labels
