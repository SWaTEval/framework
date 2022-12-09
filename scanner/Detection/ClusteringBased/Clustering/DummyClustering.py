class DummyClustering:
    def cluster(self,
                data,
                field_for_distance: str = 'hash',
                **kwargs):

        clusters = dict()
        labels = list()
        for entry in data:
            value_for_cluster = entry[field_for_distance]
            if value_for_cluster not in clusters:
                clusters[value_for_cluster] = 0

            clusters[value_for_cluster] += 1
            label = list(clusters).index(value_for_cluster)
            labels.append(label)

        n_clusters_ = len(clusters)

        return n_clusters_, labels