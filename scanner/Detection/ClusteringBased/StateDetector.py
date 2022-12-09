import json
from math import inf
from typing import List

import tlsh
from bson import ObjectId

from scanner.Base.BaseDetector import BaseDetector
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response
from scanner.Dataclasses.State import State, StateReachabilityInfo
from scanner.Detection.ClusteringBased.Clustering.DBSCANClustering import DBSCANClustering
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class StateDetector(BaseDetector):
    """
    Clustering based State Detector. Filters out duplicate states and updates the state graph using the by clustering
    the TLSH representation of the existing states.
    """

    def __init__(self,
                 for_batch: str,
                 distance_type: str = 'tlsh',
                 dbscan_additional_metric: str = None,
                 delete_collapsed: bool = False,
                 config=None):

        self._logger = get_logger("State Detector")

        # MongoDB stuff
        self._mongo_helper = MongoHelper(for_batch)
        self._states_collection = self._mongo_helper.get_states_collection()
        self._interaction_collection = self._mongo_helper.get_interactions_collection()
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()

        # Detector Parameters
        self._clustering = DBSCANClustering()

        if config:
            sc_section = config['state_detector']

            self._min_candidates_for_state_change = sc_section['delete_collapsed']

            self._field_for_distance = sc_section['field_for_distance']
            if self._field_for_distance == '':
                self._field_for_distance = 'hash'

            self._distance_type = sc_section['distance_type']
            if self._distance_type == '' or self._distance_type == 'None':
                self._distance_type = None
            self._delete_collapsed = sc_section['delete_collapsed']

            self._dbscan_additional_metric = sc_section['dbscan_additional_metric']
            if self._dbscan_additional_metric == '' or self._dbscan_additional_metric == 'None':
                self._dbscan_additional_metric = None
        else:
            self._distance_type = distance_type
            self._delete_collapsed = delete_collapsed
            self._dbscan_additional_metric = dbscan_additional_metric

        self._logger.info('Ready')
        self._logger.info('Clustering: DBSCAN')
        self._logger.info(f'Distance type: {distance_type}')
        self._logger.info(f'Delete collapsed states: {delete_collapsed}')

    def detect(self):
        self._recalculate_state_hashes()
        self._collapse_identical_states()

    def load_states_locally(self):
        states_query = self._states_collection.find({"explored": True, "collapsed": False})

        # Load data locally because of mongo cursor
        state_query_array = []
        for query in states_query:
            state_query_array.append(query)

        return state_query_array

    def _collapse_identical_states(self):
        checked_states = []

        while True:
            states_query_array = self.load_states_locally()

            current_state_query = None
            current_state_query_ind = 0
            for state_query in states_query_array:
                if state_query not in checked_states:
                    checked_states.append(state_query)
                    current_state_query = state_query
                    break
                current_state_query_ind += 1

            if current_state_query is None:
                break

            cluster_count, labels = self._clustering.cluster(data=states_query_array,
                                                             distance_type=self._distance_type,
                                                             dbscan_additional_metric=self._dbscan_additional_metric,
                                                             field_for_distance=self._field_for_distance)

            current_state_label = labels[current_state_query_ind]
            states_in_cluster = 0
            entry_ids = []
            for idx, label in enumerate(labels):
                if label == current_state_label:
                    states_in_cluster += 1
                    state = states_query_array[idx]
                    state_id = str(state['_id'])
                    entry_ids.append(state_id)

            # If more than one state (i.e. the current state) is in the same cluster then we have 2 identical states
            # And we have to collapse them into one
            if states_in_cluster > 1:
                # Find the first state
                earliest_timestamp = inf
                for entry_id in entry_ids:
                    state_query = self._states_collection.find_one({'_id': ObjectId(entry_id)})
                    state_timestamp = state_query['created_at']
                    if state_timestamp < earliest_timestamp:
                        earliest_timestamp = state_timestamp

                earliest_identical_state_query = self._states_collection.find_one({'created_at': earliest_timestamp})
                earliest_identical_state_id = str(earliest_identical_state_query['_id'])

                # Let the scanner know that it is actually in a previous state
                self._mongo_helper.update_current_state(earliest_identical_state_id)

                earliest_state_reachability: List[StateReachabilityInfo] = []

                # Merge all identical states and update their endpoints and interactions
                entry_ids.remove(earliest_identical_state_id)
                for entry_id in entry_ids:
                    entry_data = self._states_collection.find_one({'_id': ObjectId(entry_id)})
                    previous_state = self._states_collection.find_one({'_id': ObjectId(entry_data['previous_state_id'])})
                    reachability_info = StateReachabilityInfo(from_state_id=str(previous_state['_id']),
                                                              caused_by_interaction_id=entry_data['caused_by_interaction_id'])
                    earliest_state_reachability.append(reachability_info)
                    if self._delete_collapsed:
                        self._mongo_helper.delete_states_recursively(entry_id)
                    else:
                        self._mongo_helper.mark_states_as_collapsed_recursively(entry_id)
                    self._logger.info(f'Collapsed state: {entry_id}')

                self._mongo_helper.extend_state_reachability(state_id=earliest_identical_state_id,
                                                             reachability_info_list=earliest_state_reachability)

    def _recalculate_state_hashes(self):
        states_query = self._states_collection.find({"explored": True})
        for state_query in states_query:
            state_id = str(state_query['_id'])

            to_hash = self._genereate_interaction_hash_based_string(state_id)

            # This ensures that tlsh will have enough data to generate a hash
            padding = 50 * '*'
            data_bytes = (padding + to_hash).encode()
            state_hash = tlsh.hash(data_bytes)

            # If there are still no interactions, the state will still have a hash of TNULL even if the padding is added
            if state_hash == 'TNULL':
                # In this case, we generate a random hash
                state_hash = State.generate_random_hash()

            # Update state hash
            self._states_collection.find_one_and_update(state_query, {'$set': {'hash': state_hash}})

    def _generate_endpoint_based_string(self, state_id):
        # Get the interactions of the state
        endpoints_query = self._endpoints_collection.find({'state_id': state_id, 'clean': True})
        endpoints_string = ''

        for endpoint_query in endpoints_query:
            endpoint = Endpoint.from_dict(endpoint_query)

            param_list = list(endpoint.parameters)
            param_str = ""
            for param in param_list:
                param_str += param.to_json()

            endpoints_string += endpoint.host + \
                                endpoint.path + \
                                endpoint.method + \
                                endpoint.scheme + \
                                param_str

        return endpoints_string

    def _genereate_interaction_hash_based_string(self, state_id):
        # Get the interactions of the state
        interactions_query = self._interaction_collection.find({'state_id': state_id, 'made_by_fuzzer': False})
        distinct_interaction_hashes = interactions_query.distinct('hash')

        combined_hash_string = ''
        for hash in distinct_interaction_hashes:
            combined_hash_string += hash

        return combined_hash_string

    def _generate_interaction_based_string(self, state_id):
        # Get the interactions of the state
        interactions_query = self._interaction_collection.find({'state_id': state_id, 'made_by_fuzzer': False})

        # Query the interaction with different hash (to skip adding duplicates)
        distinct_interactions_hashes = interactions_query.distinct('hash')

        interactions_string = ''
        for interaction_hash in distinct_interactions_hashes:
            distinct_interaction_query = self._interaction_collection.find_one({'hash': interaction_hash})
            request = Request.from_dict(distinct_interaction_query['request'])
            response = Response.from_dict(distinct_interaction_query['response'])

            param_list = list(request.endpoint.parameters)
            param_str = ""
            for param in param_list:
                param_str += param.to_json()

            interactions_string += request.endpoint.method + \
                                   request.endpoint.url + \
                                   param_str + \
                                   json.dumps(request.headers) + \
                                   str(response.code) + \
                                   response.data

        return interactions_string
