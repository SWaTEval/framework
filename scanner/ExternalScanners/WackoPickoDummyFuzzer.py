from logging import Logger
from typing import List, Dict

from bson import ObjectId

from scanner.Base.BaseModule import BaseModule
from scanner.Crawling.Simple.SimpleInteractionHandler import SimpleInteractionHandler
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Parameter import Parameter
from scanner.Dataclasses.Request import Request
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class WackoPickoDummyFuzzer(BaseModule):
    """
    A module that acts as a fuzzer by applying known state changing request on known endpoints of Wacko Picko.
    """

    def __init__(self, for_batch: str):
        self._for_batch = for_batch
        self._mongo_helper = MongoHelper(self._for_batch)
        self._states_collection = self._mongo_helper.get_states_collection()
        self._state_fuzz_history = {}
        self._logger = get_logger("Wacko Picko Dummy Fuzzer")
        self._local_ih = SimpleInteractionHandler(for_batch=self._for_batch,
                                                  name="Fuzzer's Interaction Handler")
        self._logger.info("Ready")

    def run(self):
        current_state = self._mongo_helper.get_current_state()
        if current_state.explored and not current_state.fuzzed:
            if self.fuzz_login():
                current_state_id = self._mongo_helper.get_current_state_id()
                self._states_collection.update_one({'_id': ObjectId(current_state_id)}, {'$set': {'fuzzed': True}})

    def fuzz_login(self):
        self._logger.info("Fuzzing state machine page")
        current_state_id = self._mongo_helper.get_current_state_id()

        fuzzy_payloads = [{'username': 'scanner2', 'password': 'scanner2'},
                          {'username': 'scanner1', 'password': 'scanner1'},
                          {'username': 'not_existing', 'password': 'wontlogin'}]

        if current_state_id not in self._state_fuzz_history:
            self._state_fuzz_history[current_state_id] = fuzzy_payloads

        if len(self._state_fuzz_history[current_state_id]) > 0:
            fuzzy_payload = self._state_fuzz_history[current_state_id].pop()

            fuzzy_parameters = []
            for key, value in fuzzy_payload.items():
                fuzzy_parameters.append(Parameter(name=key, value=value))

            fuzzy_endpoint = Endpoint(host='wackopicko.docker',
                                      path='/users/login.php',
                                      method='POST',
                                      data=tuple(fuzzy_parameters),
                                      state_id=current_state_id,
                                      from_interaction_id="User defined")

            fuzzy_request = Request(fuzzy_endpoint)
            self._local_ih.execute(request=fuzzy_request,
                                   made_by_fuzzer=True)
            done = False
        else:
            done = True

        return done
