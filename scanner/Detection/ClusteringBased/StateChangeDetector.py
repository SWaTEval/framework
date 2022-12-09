from omegaconf import OmegaConf

from scanner.Base.BaseDetector import BaseDetector
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Detection.ClusteringBased.Clustering.DBSCANClustering import DBSCANClustering
from scanner.Dataclasses.Interaction import InteractionClusteringInfo
from scanner.Dataclasses.State import State
from scanner.Detection.ClusteringBased.Clustering.DummyClustering import DummyClustering
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class StateChangeDetector(BaseDetector):
    """
    Clustering based State change detector. Detects if a state transition is present by comparing the clusters of the
    interactions in the corresponding state.
    """

    def __init__(self, for_batch: str,
                 distance_type: str = 'tlsh',
                 filed_for_distance: str = 'hash',
                 dbscan_additional_metric: str = None,
                 only_interactions_from_fuzzer: bool = False,
                 config=None):

        self._logger = get_logger("State Change Detector")

        # MongoDB stuff
        self._mongo_helper = MongoHelper(for_batch)
        self._interactions_collection = self._mongo_helper.get_interactions_collection()
        self._states_collection = self._mongo_helper.get_states_collection()
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()
        self._interaction_clustering_collection = self._mongo_helper.get_interaction_clustering_collection()

        # Detector Parameters
        self._clustering = DBSCANClustering()

        if config:
            scd_section = config['state_change_detector']

            self._only_interactions_from_fuzzer = scd_section['only_interactions_from_fuzzer']

            self._field_for_distance = scd_section['field_for_distance']
            if self._field_for_distance == '':
                self._field_for_distance = 'hash'

            self._distance_type = scd_section['distance_type']
            if self._distance_type == '' or self._distance_type == 'None':
                self._distance_type = None

            self._dbscan_additional_metric = scd_section['dbscan_additional_metric']
            if self._dbscan_additional_metric == '' or self._dbscan_additional_metric == 'None':
                self._dbscan_additional_metric = None
        else:
            self._distance_type = distance_type
            self._only_interactions_from_fuzzer = only_interactions_from_fuzzer
            self._field_for_distance = filed_for_distance
            self._dbscan_additional_metric = dbscan_additional_metric

        self._logger.info('Ready')
        self._logger.info('Detection: Clustering with DBSCAN')
        self._logger.info(f'Field for distance {str(self._field_for_distance)}')
        self._logger.info(f'Distance type {str(self._distance_type)}')
        self._logger.info(f'Only on fuzzy interactions: {self._only_interactions_from_fuzzer}')

    def detect(self):
        states_query = self._states_collection.find({'explored': True,
                                                     'collapsed': False})

        if states_query is None:
            self._logger.info("No states for detection that fit the search criterion were found")

        for state_query in states_query:
            # Current state
            state_id = str(state_query['_id'])

            interactions_query_input = {"state_id": state_id,
                                        "clustering_processed": False,
                                        "made_by_fuzzer": self._only_interactions_from_fuzzer}

            interactions_count = self._interactions_collection.count_documents(interactions_query_input)

            if interactions_count == 0:
                self._logger.info(f"State {state_id} has no interaction that fit the search criterion")
                continue

            interactions_query = self._interactions_collection.find(interactions_query_input)
            for interaction_query in interactions_query:
                self._logger.info(f'Checking interaction {str(interaction_query["_id"])}')

                # Find similar interactions in the current state
                interaction_endpoint: Endpoint = Endpoint.from_dict(interaction_query['request']['endpoint'])
                similar_interactions_array = self._mongo_helper.get_similar_interactions(endpoint=interaction_endpoint,
                                                                                         state_id=state_id)

                # Append the current interaction at the last place of the array
                similar_interactions_array.append(interaction_query)

                current_cluster_info = self._mongo_helper.get_interaction_cluster_info(interaction_query)
                if current_cluster_info is None:
                    old_cluster_count = 1
                else:
                    current_cluster_info: InteractionClusteringInfo = InteractionClusteringInfo.from_dict(current_cluster_info)
                    old_cluster_count = current_cluster_info.cluster_count

                cluster_count, labels = self._clustering.cluster(data=similar_interactions_array,
                                                                 dbscan_additional_metric=self._dbscan_additional_metric,
                                                                 distance_type=self._distance_type,
                                                                 field_for_distance=self._field_for_distance)

                self._logger.info(f'Cluster delta {cluster_count - old_cluster_count} for interaction {str(interaction_query["_id"])}')

                if cluster_count > old_cluster_count:
                    self._add_new_state(old_state_id=state_id,
                                        causing_interaction_query=interaction_query)
                    self._mongo_helper.update_interaction_cluster_info(interaction_query, cluster_count)

                self._interactions_collection.find_one_and_update(interaction_query,
                                                                  {"$set": {"clustering_processed": True}})

    def _add_new_state(self, old_state_id: str, causing_interaction_query):
        new_state = State(previous_state_id=old_state_id,
                          caused_by_interaction_id=str(causing_interaction_query['_id']))
        next_state_id = self._mongo_helper.add_state(new_state)

        self._logger.info(f"New state {next_state_id} detected")

        # Update all endpoints and interactions that happened after the state changing request
        state_changing_interaction_ts = causing_interaction_query['created_at']
        self._mongo_helper.update_endpoints(after_timestamp=state_changing_interaction_ts,
                                            for_state_id=old_state_id,
                                            new_state_id=next_state_id)

        self._mongo_helper.update_interactions(after_timestamp=state_changing_interaction_ts,
                                               for_state_id=old_state_id,
                                               new_state_id=next_state_id)
