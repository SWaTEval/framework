
from logging import Logger
from queue import LifoQueue

import bson
from bson import ObjectId
from pymongo.collection import Collection

from scanner.Base.BaseModule import BaseModule
from scanner.Crawling.CrawlerExcetptions import NoResetEndpointInDB, NoMoreStatesToExplore
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Interaction import Interaction
from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.State import State
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class SimpleStateNavigator(BaseModule):

    """
    This state navigator picks the first state that is not fully explored. If all states are fully explored
    the next state will be a state that has endpoints not fuzzed by a fuzzer.
    """

    def __init__(self, for_batch: str, max_revisits: int = 3, config=None):
        """
        :param for_batch: Name of the batch containing information about the current app scan in the DB
        :type for_batch: str

        :param max_revisits: How many times the state endpoints should be revisited, before a state is flagged as explored.
        :type config: int

        :param config: Custom configuration settings
        :type config: dict
        """

        self._mongo_helper = MongoHelper(for_batch)
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()
        self._interactions_collection = self._mongo_helper.get_interactions_collection()
        self._states_collection = self._mongo_helper.get_states_collection()

        app_reset_endpoint_query = self._endpoints_collection.find_one({'is_reset': True})
        if app_reset_endpoint_query is None:
            raise NoResetEndpointInDB('Make sure you have an app resetting endpoint in the DB. ' +
                                       'It is needed to reset the app when a state change is detected.')

        self._app_reset_endpoint = Endpoint.from_dict(app_reset_endpoint_query)

        if config:
            sn_section = config['state_navigator']
            self._max_revisits = sn_section['max_revisits']
        else:
            self._max_revisits = max_revisits

        self._logger = get_logger("State Navigator")
        self._logger.info("Ready")

    def run(self) -> LifoQueue:
        """
        Creates a navigation queue to the first non fully explored or non fully fuzzed state

        :raises NoMoreStatesToExplore: If the all endpoints in all states are visited and fuzzed this
        exception will be risen.

        :return: Queue containing all requests needed to put the app in the corresponding state
        :rtype: LifoQueue
        """
        self._mongo_helper.update_states_explored_status()

        current_state_id = self._mongo_helper.get_current_state_id()
        current_state_unexplored_endpoints = self._mongo_helper.get_unexplored_endpoints_count(current_state_id)
        current_state = self._mongo_helper.get_current_state()

        # Reset the app always for now, just be on the safe side that the proper state is reached
        # TODO: Implement logic that resets the app only when a state change is detected
        reset_app = True

        if current_state_unexplored_endpoints > 0:
            next_state_id = current_state_id
        else:
            if current_state.revisits < self._max_revisits:
                self._mongo_helper.mark_state_for_revisit(current_state_id)
                self._mongo_helper.set_current_state_revisit_count(current_state.revisits + 1)
                next_state_id = current_state_id
            else:
                next_state_id = self._mongo_helper.get_unexplored_state_id()

                if next_state_id is None:
                    next_state_id = self._mongo_helper.get_non_fuzzed_state_id()

                    if next_state_id is None:
                        raise NoMoreStatesToExplore("All endpoints in all states were explored and fuzzed")

        # Mark the next state as current in the db
        self._mongo_helper.update_current_state(next_state_id)

        # Generate navigation queue to the next state for the interaction handler
        navigation_queue = self.generate_navigation_queue(goal_state_id=next_state_id,
                                                          reset_app=reset_app)

        return navigation_queue

    def generate_navigation_queue(self, goal_state_id: str, reset_app: bool) -> LifoQueue:
        """
        Generate a navigation queue to a goal state

        :param goal_state_id: State id of the goal state
        :type goal_state_id: str

        :param reset_app: If True an app resetting request is added in the start of the queue
        :type reset_app: bool

        :return: Queue containing all requests needed to put the app in the corresponding state
        :rtype: LifoQueue
        """
        # Find the series of request that lead to this state
        request_queue = LifoQueue()

        # Get the goal state data
        goal_state_query = self._states_collection.find_one({"_id": ObjectId(goal_state_id)})
        goal_state: State = State.from_dict(goal_state_query)

        # Try to convert the interaction id to ObjectId for mongo query
        # Handle the case where the initial state has no real initial interaction and the interaction id
        # can't get converted to ObjectId
        try:
            causing_interaction_id = ObjectId(goal_state.caused_by_interaction_id)
        except bson.errors.InvalidId:
            # If we want to go back to the initial state, we just have to reset the app
            app_reset_request = Request(endpoint=self._app_reset_endpoint)
            request_queue.put(app_reset_request)
            return request_queue

        # Get the interaction data that led to the goal state
        causing_interaction_query = self._interactions_collection.find_one({"_id": causing_interaction_id})
        causing_interaction = Interaction.from_dict(causing_interaction_query)

        # Enqueue the request
        request_queue.put(causing_interaction.request)

        # Redo the operations till the root state is reached
        state = goal_state
        while True:
            state_query = self._states_collection.find_one({"_id": ObjectId(state.previous_state_id)})
            state = State.from_dict(state_query)

            if not state.initial:
                interaction_query = self._interactions_collection.find_one(
                    {"_id": ObjectId(state.caused_by_interaction_id)})
                interaction = Interaction.from_dict(interaction_query)
                request_queue.put(interaction.request)
            else:
                break

        if reset_app:
            app_reset_request = Request(endpoint=self._app_reset_endpoint)
            request_queue.put(app_reset_request)

        return request_queue
