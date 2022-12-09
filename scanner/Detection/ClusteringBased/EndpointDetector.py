from bson import ObjectId

from scanner.Base.BaseDetector import BaseDetector
from scanner.Dataclasses.Endpoint import Endpoint, EndpointClusteringInfo
from scanner.Detection.ClusteringBased.Clustering.DBSCANClustering import DBSCANClustering
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class EndpointDetector(BaseDetector):
    """
    Clustering Based Endpoint Detector. Detects if a new Endpoint is found based on the clusters in the already
    existing data in the DB.
    """

    def __init__(self,
                 for_batch: str,
                 distance_type: str = 'tlsh',
                 dbscan_additional_metric: str = None,
                 delete_dirty: bool = False,
                 config=None):
        # MongoDB Stuff
        self._mongo_helper = MongoHelper(for_batch=for_batch)
        self._interactions_collection = self._mongo_helper.get_interactions_collection()
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()
        self._endpoint_clustering_collection = self._mongo_helper.get_endpoint_clustering_collection()

        self._logger = get_logger("Endpoint Detector")

        # Detector Parameters
        self._clustering = DBSCANClustering()

        if config:
            ec_section = config['endpoint_detector']

            self._field_for_distance = ec_section['field_for_distance']
            if self._field_for_distance == '':
                self._field_for_distance = 'hash'

            self._distance_type = ec_section['distance_type']
            if self._distance_type == '' or self._distance_type == 'None':
                self._distance_type = None
            self._delete_dirty = ec_section['delete_dirty']

            self._dbscan_additional_metric = ec_section['dbscan_additional_metric']
            if self._dbscan_additional_metric == '' or self._dbscan_additional_metric == 'None':
                self._dbscan_additional_metric = None
        else:
            self._distance_type = distance_type
            self._delete_dirty = delete_dirty
            self._dbscan_additional_metric = dbscan_additional_metric

        self._logger.info('Ready')
        self._logger.info('Clustering: DBSCAN')
        self._logger.info(f'Distance type: {distance_type}')
        self._logger.info(f'Delete dirty endpoints: {delete_dirty}')

    def detect(self):
        endpoints_query = self._endpoints_collection.find({'clustering_processed': False})

        for endpoint_query in endpoints_query:
            endpoint_id = str(endpoint_query['_id'])
            endpoint = Endpoint.from_dict(endpoint_query)
            similar_endpoints = self._mongo_helper.get_similar_endpoints(endpoint)

            # Calculate the cluster count of the similar endpoints
            cluster_count, labels = self._clustering.cluster(data=similar_endpoints,
                                                             distance_type=self._distance_type,
                                                             dbscan_additional_metric=self._dbscan_additional_metric,
                                                             field_for_distance=self._field_for_distance)

            # Check if the cluster count has changed
            cluster_count_changed = self._cluster_count_changed(endpoint, cluster_count)

            self._endpoints_collection.find_one_and_update({'_id': ObjectId(endpoint_id)}, {'$set': {'clustering_processed': True}})

            if not cluster_count_changed and len(similar_endpoints) > cluster_count:
                self._logger.info(f'Endpoint {endpoint_id} marked as dirty')
                if self._delete_dirty:
                    self._endpoints_collection.delete_one({'_id': ObjectId(endpoint_id)})
                    self._logger.info(f'Endpoint {endpoint_id} deleted')
            else:
                self._endpoints_collection.find_one_and_update({'_id': ObjectId(endpoint_id)}, {'$set': {'clean': True}})

    def _cluster_count_changed(self, endpoint: Endpoint, current_cluster_count: int):
        changed = False
        query = EndpointClusteringInfo(host=endpoint.host,
                                       scheme=endpoint.scheme,
                                       path=endpoint.path,
                                       method=endpoint.method,
                                       state_id=endpoint.state_id,
                                       cluster_count=0)

        query = query.to_dict()
        query.pop('cluster_count')

        cluster_info_query = self._endpoint_clustering_collection.find_one(query)

        if cluster_info_query is not None:
            old_cluster_count = cluster_info_query['cluster_count']

            if current_cluster_count > old_cluster_count:
                changed = True
                self._endpoint_clustering_collection.update_one(cluster_info_query,
                                                                {'$set': {'cluster_count': current_cluster_count}})
        else:
            new_cluster_info_entry = query
            new_cluster_info_entry['cluster_count'] = current_cluster_count
            self._endpoint_clustering_collection.insert_one(new_cluster_info_entry)
            changed = True

        return changed
