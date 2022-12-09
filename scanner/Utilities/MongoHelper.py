import json
from copy import deepcopy
from logging import Logger
from math import inf
from typing import List

from bson import ObjectId
from omegaconf import OmegaConf
from pymongo import MongoClient
from pymongo.collection import Collection

from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Interaction import Interaction, InteractionClusteringInfo
from scanner.Dataclasses.State import State, NoStateMarkedAsCurrent, StateReachabilityInfo
from scanner.Utilities.Logging import get_logger


class MongoHelper:
    """
    A helper class for communication with Mongo implementing often reaping methods.
    """

    def _read_config(self):
        config = OmegaConf.load('config.yaml')

        mongo_credentials_section = config['mongo_db_credentials']
        self._username = mongo_credentials_section['username']
        self._password = mongo_credentials_section['password']
        self._host = mongo_credentials_section['mongo_host']
        self._port = mongo_credentials_section['mongo_port']

        mongo_db_names_section = config['mongo_db_names']
        self._endpoints_db_name = mongo_db_names_section['endpoints']
        self._interactions_db_name = mongo_db_names_section['interactions']
        self._states_db_name = mongo_db_names_section['states']
        self._endpoint_clustering_db_name = mongo_db_names_section['endpoint_clustering']
        self._interaction_clustering_db_name = mongo_db_names_section['interaction_clustering']

    def __init__(self, for_batch: str):
        """
        :param for_batch: Name of new collections in the Mongo DB sections
        :type for_batch: str

        :return: Instance of MongoHelper that holds a connection to the DB
        :rtype: MongoHelper

        :raises ConnectionError: When the connection fails because of bad credentials or host setup
        """

        self._logger = get_logger("Mongo Helper")
        self._for_batch = for_batch
        self._read_config()

        self._client = MongoClient(host=self._host,
                                   port=self._port,
                                   username=self._username,
                                   password=self._password)

        # Check server connection
        try:
            self._client.server_info()
        except:
            raise ConnectionError("Something went wrong when trying to connect to mongo host")

    def add_params(self, config):
        config_copy = deepcopy(config)
        client = self.get_client()
        batch_name = self.get_batch_name()

        # Stringify the key, because bson can't parse omegaconf.listconfig.ListConfig and breaks the logic
        config_copy['state_change_detector']['field_for_distance'] = str(config_copy['state_change_detector']['field_for_distance'])
        client['experiments'][batch_name].insert_one(config_copy)

    def add_endpoint(self, endpoint: Endpoint) -> str:
        """
        Add a new :class:`Endpoint` to the DB

        :param endpoint: The :class:`Endpoint` to be added
        :type endpoint: Endpoint

        :return: Created :class:`Endpoint` id
        :rtype: str
        """

        endpoints_collection = self.get_endpoints_collection()
        result = endpoints_collection.insert_one(endpoint.to_dict())
        return str(result.inserted_id)

    def add_state(self, state: State) -> str:
        """
        Add a new :class:`State` to the DB

        :param state: The :class:`State` to be added
        :type state: State

        :return: Created :class:`State` id
        :rtype: str
        """

        states_collection = self.get_states_collection()
        result = states_collection.insert_one(state.to_dict())
        return str(result.inserted_id)

    def add_interaction(self, interaction: Interaction) -> str:
        """
        Add a new :class:`Interaction` to the DB

        :param interaction: The :class:`Interaction` to be added
        :type interaction: Interaction

        :return: Created :class:`Interaction` id
        :rtype: str
        """

        interactions_collection = self.get_interactions_collection()
        result = interactions_collection.insert_one(interaction.to_dict())
        return str(result.inserted_id)

    def get_current_state_id(self) -> str:
        """
        :return: Current :class:`State` id
        :rtype: str
        """

        states_collection = self.get_states_collection()
        state_query = states_collection.find_one({'current': True})
        if state_query is None:
            current_state_id = None
            # raise NoStateMarkedAsCurrent("There is no current state in mongo")
        else:
            current_state_id = str(state_query['_id'])
        return current_state_id

    def get_current_state(self) -> State:
        """
        :return: Current :class:`State`
        :rtype: State
        """
        states_collection = self.get_states_collection()
        state_query = states_collection.find_one({'current': True})
        if state_query is None:
            current_state = None
        else:
            current_state = State.from_dict(state_query)
        return current_state

    def set_current_state_revisit_count(self, revisits_count: int):
        """
        Updates the number of times the state was revisited

        :param revisits_count: Number of times the state was revisited
        :type revisits_count: int
        """
        states_collection = self.get_states_collection()
        current_state_id = self.get_current_state_id()
        states_collection.find_one_and_update({'_id': ObjectId(current_state_id)},
                                              {'$set': {'revisits': revisits_count}})

    def update_current_state(self, state_id: str):
        """
        Marks the input state id as current

        :param state_id: Target state id
        :type state_id: str
        """
        states_collection = self.get_states_collection()
        states_collection.find_one_and_update({'current': True}, {'$set': {'current': False}})
        states_collection.find_one_and_update({'_id': ObjectId(state_id)}, {'$set': {'current': True}})

    def get_client(self) -> MongoClient:
        """
        :return: The DB client of the current MongoHelper instance
        :rtype: MongoClient
        """

        # Create a connection to mongo db
        return self._client

    def get_endpoints_collection(self) -> Collection:
        """
        :return: The endpoints collection of the current batch
        :rtype: Collection
        """

        client = self.get_client()
        endpoints_collection = client[self._endpoints_db_name][self._for_batch]
        return endpoints_collection

    def get_interactions_collection(self) -> Collection:
        """
        :return: The interactions collection of the current batch
        :rtype: Collection
        """

        client = self.get_client()
        interactions_collection = client[self._interactions_db_name][self._for_batch]
        return interactions_collection

    def get_states_collection(self) -> Collection:
        """
        :return: The states collection of the current batch
        :rtype: Collection
        """

        client = self.get_client()
        states_collection = client[self._states_db_name][self._for_batch]
        return states_collection

    def get_endpoint_clustering_collection(self) -> Collection:
        """
        :return: The endpoints clustering collection of the current batch
        :rtype: Collection
        """

        client = self.get_client()
        endpoint_clustering_collection = client[self._endpoint_clustering_db_name][self._for_batch]
        return endpoint_clustering_collection

    def get_interaction_clustering_collection(self) -> Collection:
        """
        :return: The interactions clustering collection of the current batch
        :rtype: Collection
        """

        client = self.get_client()
        interaction_clustering_collection = client[self._interaction_clustering_db_name][self._for_batch]
        return interaction_clustering_collection

    def clear_whole_db(self):
        """
        Deletes all data in the DB
        """

        client = self.get_client()
        dbs = client.list_database_names()
        dbs.remove('admin')
        for db in dbs:
            client.drop_database(db)

    def clear_current_batch(self):
        """
        Deletes the current batch data in the DB
        """

        client = self.get_client()
        batch_name = self.get_batch_name()
        dbs = client.list_database_names()

        for db in dbs:
            client[db].drop_collection(batch_name)

    def get_similar_interactions(self, endpoint: Endpoint, state_id: str, processed_type: str = '', fuzzed_type: str = '') -> List[dict]:
        """
        Finds similar interactions in the DB by endpoint comparison
        (Note: only the host, method, scheme, path and state_id of the endpoint are compared)

        :param endpoint: The endpoint used for comparison
        :type endpoint: Endpoint

        :param state_id: Id of the state where the interactions will be searched for
        :type state_id: str

        :param processed_type: Use this parameter if you want to add processed constraint to the query (valid input 'processed, 'non-processed' or empty string for none)
        :type processed_type: str

        :param fuzzed_type: Use this parameter if you want to add fuzzed constraint to the query (valid input 'fuzzed, 'non-fuzzed' or empty string for none)
        :type fuzzed_type: str

        :return: A list of similar interactions
        :rtype: List[dict]  (dict contains the data of a non cast :class:`Interaction`)
        """

        interactions_collection = self.get_interactions_collection()

        interactions_query = {"request.endpoint.host": endpoint.host,
                              "request.endpoint.method": endpoint.method,
                              "request.endpoint.scheme": endpoint.scheme,
                              "request.endpoint.path": endpoint.path,
                              "state_id": state_id
                              }

        if processed_type == "processed":
            interactions_query['clustering_processed'] = True
        elif processed_type == 'non-processed':
            interactions_query['clustering_processed'] = False

        if fuzzed_type == "fuzzed":
            interactions_query["made_by_fuzzer"] = True
        elif fuzzed_type == 'non-fuzzed':
            interactions_query["made_by_fuzzer"] = False

        similar_interactions_query = interactions_collection.find(interactions_query)

        similar_interactions = []
        for interaction_query in similar_interactions_query:
            similar_interactions.append(interaction_query)

        return similar_interactions

    def get_similar_endpoints(self, endpoint: Endpoint) -> List[dict]:
        """
        Finds similar endpoints in the DB compared to a target endpoint

        :param endpoint: Endpoint used for comparison
        :type endpoint: Endpoint

        :return: A list of similar endpoints
        :rtype: List[dict]  (dict contains the data of a non casted :class:`Endpoint`)
        """
        endpoints_collection = self.get_endpoints_collection()

        # Find all similar endpoints in same state
        query = {"host": endpoint.host,
                 "method": endpoint.method,
                 "scheme": endpoint.scheme,
                 "path": endpoint.path,
                 "state_id": endpoint.state_id,
                 "found_at": endpoint.found_at}

        similar_endpoints = endpoints_collection.find(query)

        # Load locally because the mongo cursor iterates simultaneously
        similar_endpoints_array = []
        for query in similar_endpoints:
            similar_endpoints_array.append(query)

        return similar_endpoints_array

    def update_endpoints(self, after_timestamp: int, for_state_id: str, new_state_id: str):
        """
        Changes the endpoints owner state id after specific timestamp

        :param after_timestamp: Unix time in milliseconds after which the state of any created endpoint will be updated
        :type after_timestamp: int

        :param for_state_id: State id owner of the endpoints that will be updated
        :type for_state_id: str

        :param new_state_id: New state id owner of the endpoints
        :type new_state_id: str
        """

        endpoints_collection = self.get_endpoints_collection()
        query = {
            "state_id": for_state_id,
            "created_at": {"$gt": after_timestamp}
        }

        endpoints_query = endpoints_collection.find(query)
        if endpoints_query is not None:
            for endpoint_query in endpoints_query:
                endpoints_collection.find_one_and_update(endpoint_query, {"$set": {"state_id": new_state_id,
                                                                                   'allow_visit': True,
                                                                                   'clustering_processed': False}})

    def delete_endpoints(self, after_timestamp: int, for_state_id: str):
        """
        Delete the endpoints of an owner state id after specific timestamp

        :param after_timestamp: Unix time in milliseconds after which the endpoints of the owner state will be deleted
        :type after_timestamp: int

        :param for_state_id: State id owner of the interactions that will be updated
        :type for_state_id: str
        """

        endpoints_collection = self.get_endpoints_collection()

        query = {
            "state_id": for_state_id,
            "created_at": {"$gt": after_timestamp}
        }

        endpoints_query = endpoints_collection.find(query)
        if endpoints_query is not None:
            for endpoint_query in endpoints_query:
                endpoints_collection.delete_one(endpoint_query)

    def update_interactions(self, after_timestamp: int, for_state_id: str, new_state_id: str):
        """
        Changes the interactions owner state id after specific timestamp

        :param after_timestamp: Unix time in milliseconds after which the state of any created interaction  will be updated
        :type after_timestamp: int

        :param for_state_id: State id owner of the interactions that will be updated
        :type for_state_id: str

        :param new_state_id: New state id owner of the interactions
        :type new_state_id: str
        """

        interactions_collection = self.get_interactions_collection()
        query = {
            "state_id": for_state_id,
            "created_at": {"$gt": after_timestamp}
        }

        interactions_query = interactions_collection.find(query)
        if interactions_query is not None:
            for interaction_query in interactions_query:
                interactions_collection.find_one_and_update(interaction_query, {"$set": {"state_id": new_state_id}})

    def delete_interactions(self, after_timestamp: int, for_state_id: str):
        """
        Delete the endpoints of an owner state id after specific timestamp

        :param after_timestamp: Unix time in milliseconds after which the endpoints of the owner state will be deleted
        :type after_timestamp: int

        :param for_state_id: State id owner of the interactions that will be updated
        :type for_state_id: str
        """

        interactions_collection = self.get_interactions_collection()
        query = {
            "state_id": for_state_id,
            "created_at": {"$gt": after_timestamp}
        }

        interactions_query = interactions_collection.find(query)
        if interactions_query is not None:
            for interaction_query in interactions_query:
                interactions_collection.delete_one(interaction_query)

    def get_interaction_cluster_info(self, interaction_query: dict) -> InteractionClusteringInfo:
        """
        Read the previous clustering information of an :class:`Interaction`

        :param interaction_query: A dict containing the interaction for which will be used as DB query
        :type: dict (non casted :class:`Interaction`)

        :return: The clustering information of the searched interaction
        :rtype: InteractionClusteringInfo
        """
        interaction_clustering_collection = self.get_interaction_clustering_collection()
        interaction_cluster_info_base = InteractionClusteringInfo(
            request_endpoint_host=interaction_query['request']['endpoint']['host'],
            request_endpoint_scheme=interaction_query['request']['endpoint']['scheme'],
            request_endpoint_path=interaction_query['request']['endpoint']['path'],
            request_endpoint_method=interaction_query['request']['endpoint']['method'],
            state_id=interaction_query['state_id'],
            cluster_count=0)
        query = interaction_cluster_info_base.to_dict()
        query.pop('cluster_count')

        cluster_info_query = interaction_clustering_collection.find_one(query)

        if cluster_info_query is not None:
            cluster_info = InteractionClusteringInfo.from_dict(cluster_info_query)
        else:
            cluster_info = None
        return cluster_info

    def update_interaction_cluster_info(self, interaction_query: dict, new_cluster_count: int):
        """
        Update the cluster count of an interaction

        :param interaction_query: Dict containing the data of the interaction that will be updated
        :type interaction_query: dict (non casted :class:`Interaction`)

        :param new_cluster_count: The new cluster count of the interaction
        :type new_cluster_count: int
        """

        interaction_clustering_collection = self.get_interaction_clustering_collection()
        cluster_info = self.get_interaction_cluster_info(interaction_query)

        if cluster_info is not None:
            interaction_clustering_collection.update_one(cluster_info.to_dict(),
                                                         {'$set': {'cluster_count': new_cluster_count}})
        else:
            new_cluster_info_entry = InteractionClusteringInfo(
                request_endpoint_host=interaction_query['request']['endpoint']['host'],
                request_endpoint_scheme=interaction_query['request']['endpoint']['scheme'],
                request_endpoint_path=interaction_query['request']['endpoint']['path'],
                request_endpoint_method=interaction_query['request']['endpoint']['method'],
                state_id=interaction_query['state_id'],
                cluster_count=new_cluster_count)
            interaction_clustering_collection.insert_one(new_cluster_info_entry.to_dict())

    def extend_state_reachability(self, state_id: str, reachability_info_list: List[StateReachabilityInfo]):
        """
        Adds data for the reachability of a state from another state

        :param state_id: The id of the state that will be updated
        :type state_id: str

        :param reachability_info_list: A list containing the new reachability data
        :type reachability_info_list: StateReachabilityInfo
        """

        states_collection = self.get_states_collection()
        for reachability_info in reachability_info_list:
            states_collection.find_one_and_update({'_id': ObjectId(state_id)},
                                                  {'$push': {'reachable_from': reachability_info.to_dict()}})

    def mark_states_as_collapsed_recursively(self, state_id):
        """
        Mark the given parent states and all descendant states as collapsed

        :param state_id: Id of the parent state which must be marked as collapsed
        :type state_id: str
        """

        states_collection = self.get_states_collection()
        states_query = states_collection.find({"previous_state_id": state_id})
        if states_query is not None:
            for state_query in states_query:
                self.mark_states_as_collapsed_recursively(str(state_query['_id']))

        states_collection.update_one({'_id': ObjectId(state_id)}, {'$set': {'collapsed': True}})

    def delete_states_recursively(self, state_id: str):
        """
        Delete the given parent states and all descendant states

        :param state_id: Id of the parent state which must be deleted
        :type state_id: str
        """

        interactions_collection = self.get_interactions_collection()
        endpoints_collection = self.get_endpoints_collection()
        states_collection = self.get_states_collection()

        states_query = states_collection.find({"previous_state_id": state_id})
        if states_query is not None:
            for state_query in states_query:
                self.delete_states_recursively(str(state_query['_id']))

        interactions_collection.delete_many({'state_id': state_id})
        endpoints_collection.delete_many({'state_id': state_id})
        states_collection.delete_one({'_id': ObjectId(state_id)})

    @staticmethod
    def find_earliest_entry(collection: Collection, entry_ids: List[str]) -> str:
        """
        Find the earliest entry in the DB from a list of entry ids and a given collection

        :param collection: The collection in the DB where the entries will be searched
        :type collection: Collection

        :param entry_ids: List of entry ids which will be checked
        :type entry_ids: List[str]

        :return: Earliest entry id from the given list
        :rtype: str
        """

        earliest_timestamp = inf
        earliest_entry_id = ''

        for entry_id in entry_ids:
            entry_query = collection.find_one({'_id': ObjectId(entry_id)})
            entry_timestamp = int(entry_query['created_at'])
            if earliest_timestamp >= entry_timestamp:
                earliest_timestamp = entry_timestamp
                earliest_entry_id = entry_id

        return earliest_entry_id

    def mark_state_for_revisit(self, state_id: str):
        """
        Marks the specified state for revisit

        :param state_id: Id of the state which should be marked
        :type state_id: str

        Note: The endpoints of the state are labeled as unexplored
        """

        endpoints_collection = self.get_endpoints_collection()
        states_collection = self.get_states_collection()

        self._logger.info(f'Marking endpoints of state {state_id} for revisit')
        endpoints_collection.update_many({'state_id': state_id}, {'$set': {'visited': False}})
        states_collection.find_one_and_update({'_id': ObjectId(state_id)}, {'$set': {'explored': False}})

    def mark_all_interactions_for_reclustering(self):
        """
        Marks all interaction of the current batch as not processed by the clustering algorithm
        """

        interactions_collection = self.get_interactions_collection()
        interactions_collection.update_many({}, {'$set': {'clustering_processed': False}})

    def update_states_explored_status(self):
        """
        Updates the 'explored' status of every state by checking the its endpoints
        """

        states_collection = self.get_states_collection()
        states_query = states_collection.find({'collapsed': False})

        for state_query in states_query:
            state_id = str(state_query['_id'])
            unexplored_endpoints_count = self.get_unexplored_endpoints_count(state_id)

            if unexplored_endpoints_count > 0:
                states_collection.update_one({'_id': ObjectId(state_id)}, {'$set': {'explored': False}})
            else:
                states_collection.update_one({'_id': ObjectId(state_id)}, {'$set': {'explored': True}})

    def get_unexplored_endpoints_count(self, state_id: str) -> int:
        """
        :param state_id: Id of the state where the endpoints are going to be searched for
        :type state_id: str

        :return: The count of endpoints marked as not visited in the given state
        :rtype: int
        """

        endpoints_collection = self.get_endpoints_collection()
        unexplored_endpoints_count = endpoints_collection.count_documents({'state_id': state_id,
                                                                           'allow_visit': True,
                                                                           'visited': False,
                                                                           'clean': True})
        return unexplored_endpoints_count

    def get_unexplored_state_id(self) -> str:
        """
        Finds a state in the DB which is not marked as explored

        :return: The found state id or None if no state is found
        :rtype: str
        """

        self._logger.info('Checking for not fully explored states')
        states_collection = self.get_states_collection()
        state_query = states_collection.find_one({"explored": False, 'collapsed': False})

        if state_query is None:
            state_id = None
            self._logger.info('No unexplored states found.')
        else:
            state_id = str(state_query['_id'])
            self._logger.info(f'Unexplored state found. Next state will be {state_id}')

        return state_id

    def get_non_fuzzed_state_id(self) -> str:
        """
        Finds a state in the DB which is not marked as fuzzed

        :return: The found state id or None if no state is found
        :rtype: str
        """

        self._logger.info('Checking for not fully fuzzed states')
        states_collection = self.get_states_collection()
        state_query = states_collection.find_one({"fuzzed": False, 'collapsed': False})

        if state_query is None:
            state_id = None
            self._logger.info('No states for fuzzing found.')
        else:
            state_id = str(state_query['_id'])
            self._logger.info(f'Non fully fuzzed state found. Next state will be {state_id}')

        return state_id

    def get_batch_name(self) -> str:
        """
            :return: The batch name
            :rtype: str
        """
        return self._for_batch

    def get_initial_state_id(self) -> str:
        """
        Finds the initial state id

        :return: The initial state id
        :rtype: str
        """

        states_collection = self.get_states_collection()
        state_query = states_collection.find_one({"initial": True})
        initial_state_id = str(state_query['_id'])
        return initial_state_id

    def get_latest_collection_in_db(self, db_name):
        client = self.get_client()
        db = client[db_name]
        last_collection = db.list_collection_names()[-1]
        return last_collection