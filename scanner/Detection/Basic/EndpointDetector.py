from bson import ObjectId

from scanner.Base.BaseDetector import BaseDetector
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Detection.ClusteringBased.Clustering.DBSCANClustering import DBSCANClustering
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class EndpointDetector(BaseDetector):
    """
    Simple Endpoint Detector that filters similar Endpoint based on their URL
    """

    def __init__(self,
                 for_batch: str,
                 delete_dirty: bool = False,
                 config=None):
        # MongoDB Stuff
        self._mongo_helper = MongoHelper(for_batch=for_batch)
        self._interactions_collection = self._mongo_helper.get_interactions_collection()
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()

        self._logger = get_logger("Endpoint Detector")

        if config:
            ec_section = config['endpoint_detector']

            self._field_for_distance = ec_section['field_for_distance']
            if self._field_for_distance == '':
                self._field_for_distance = 'hash'

            self._distance_type = ec_section['distance_type']
            if self._distance_type == '' or self._distance_type == 'None':
                self._distance_type = None
            self._delete_dirty = ec_section['delete_dirty']

        else:
            self._delete_dirty = delete_dirty

        self._logger.info('Ready')
        self._logger.info(f'Delete dirty endpoints: {delete_dirty}')

    def detect(self):
        endpoints_query = self._endpoints_collection.find({'clustering_processed': False})

        for endpoint_query in endpoints_query:
            endpoint_id = str(endpoint_query['_id'])
            endpoint = Endpoint.from_dict(endpoint_query)
            similar_endpoints = self._mongo_helper.get_similar_endpoints(endpoint)

            endpoint_fields = {'clustering_processed': True}
            if len(similar_endpoints) == 0:
                endpoint_fields['clean'] = True
            else:
                if self._delete_dirty:
                    self._endpoints_collection.delete_one({'_id': ObjectId(endpoint_id)})
                    self._logger.info(f'Endpoint {endpoint_id} deleted')

            self._endpoints_collection.find_one_and_update({'_id': ObjectId(endpoint_id)}, {'$set': endpoint_fields})

