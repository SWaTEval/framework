from sklearn.preprocessing import MinMaxScaler

from scanner.Utilities.Distance import Distance
from scanner.Utilities.Util import extract_hashes, generate_hash2vec_dataset


class NoDistanceTypeConfiguration(Exception):
    pass


def shorten_range(x):
    if x >= 58:
        x = x - 7
    return x


def preprocess_data(distance_type, data, dbscan_additional_metric, field_for_index, field_for_distance):
    # Hash2Vec approach
    if distance_type == "hash2vec":
        if dbscan_additional_metric is None:
            clustering_metric = "euclidean"
        else:
            clustering_metric = dbscan_additional_metric
        hashes = extract_hashes(data)
        preprocessed_data = generate_hash2vec_dataset(hashes)

        # Normalize the dataframe
        preprocessed_data = preprocessed_data.applymap(shorten_range)
        preprocessed_data = (preprocessed_data - 48) / (83 - 48)

    # Option for precomputed pair-wise distances (for example when using the datasets from other papers)
    elif distance_type == "precomputed":
        clustering_metric = "precomputed"
        # Scale the data between 0 and 1 (needed for silhouette_score)
        scaler = MinMaxScaler()
        preprocessed_data = scaler.fit_transform(data)

    elif distance_type == "" or distance_type is None:
        raise NoDistanceTypeConfiguration("Missing distance type in one of your modules")

    # Distance Matrix with self selected approach
    else:
        clustering_metric = "precomputed"
        # Create a distance matrix
        distance_matrix = Distance().generate_distance_matrix(data_query=data,
                                                              distance_type=distance_type,
                                                              field_for_index=field_for_index,
                                                              field_for_distance=field_for_distance)

        # Scale the data between 0 and 1 (needed for silhouette_score)
        scaler = MinMaxScaler()
        preprocessed_data = scaler.fit_transform(distance_matrix)

    # Clustering metric returns a metric type for the clustering algorithm
    # If you extend the function make sure you choose a suitable clustering metric
    # Currently the only clustering algorithms from sklearn are used, so the suitable metrics
    # are the one available in the skleanr librarz
    return clustering_metric, preprocessed_data
