from logging import Logger
from typing import List, Dict
from urllib.parse import urlparse

from bson import ObjectId

from scanner.Base.BaseModule import BaseModule
from scanner.Crawling.Simple.SimpleInteractionHandler import SimpleInteractionHandler
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Parameter import Parameter
from scanner.Dataclasses.Request import Request
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class EvaluationFrameworkDummyFuzzer(BaseModule):
    """
    A module that acts as a fuzzer by applying known state changing request on known endpoints of the Evaluation Framework.
    """

    def __init__(self, for_batch: str, app_address: str):
        self._for_batch = for_batch
        self._mongo_helper = MongoHelper(self._for_batch)
        self._states_collection = self._mongo_helper.get_states_collection()
        self._state_fuzz_history = {}
        self._logger = get_logger("Dummy Fuzzer")
        self._local_ih = SimpleInteractionHandler(self._for_batch, name="Fuzzer's Interaction Handler")
        self._logger.info("Ready")

        parsed_url = urlparse(app_address)
        host = parsed_url.netloc

        self._state_machine_endpoint = Endpoint(host=host,
                                                path='/views/state',
                                                state_id="User defined",
                                                clean=True,
                                                clustering_processed=True,
                                                method="GET",
                                                from_interaction_id="User defined")

    def run(self):
        current_state = self._mongo_helper.get_current_state()
        if current_state.explored and not current_state.fuzzed:
            if self.fuzz_state_machine():
                current_state_id = self._mongo_helper.get_current_state_id()
                self._states_collection.update_one({'_id': ObjectId(current_state_id)}, {'$set': {'fuzzed': True}})

    def fuzz_state_machine(self):
        self._logger.info("Fuzzing state machine page")
        payloads = ['state2_2', 'state3_1', 'state3_2', 'state3_3', 'state3_4', 'special', 'initial', 'state2_1']

        current_state_id = self._mongo_helper.get_current_state_id()

        if current_state_id not in self._state_fuzz_history:
            self._state_fuzz_history[current_state_id] = payloads

        if len(self._state_fuzz_history[current_state_id]) > 0:
            fuzz_keyword = self._state_fuzz_history[current_state_id].pop()

            state_machine_endpoint = self._state_machine_endpoint
            state_machine_endpoint.parameters = (Parameter(name="keyword",
                                                           value=fuzz_keyword),)

            state_machine_request = Request(state_machine_endpoint)
            self._local_ih.execute(request=state_machine_request, made_by_fuzzer=True)
            done = False
        else:
            done = True

        return done
