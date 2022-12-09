import json
from logging import Logger

from pymongo.collection import Collection
from requests import Session

from scanner.Base.BaseInteractionHandler import BaseInteractionHandler, NoMoreEndpoints
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Interaction import Interaction
from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper

session = Session()

def get_session_object():
    """
    Get the global session object which contains headers, tokens and cookies
    """
    global session
    return session


class SimpleInteractionHandler(BaseInteractionHandler):
    """
    This interaction handler can execute manually created requests and automatically generate request to
    unseen endpoints by taking in consideration the current state of the web app.
    """

    def __init__(self, for_batch: str, name: str = "Interaction Handler", with_logger: bool = True, config=None):
        """
        :param for_batch: Name of the batch containing information about the current app scan in the DB
        :type for_batch: str

        :param name: Name of the interaction handler. Helps to present data in the logs when multiple interactions
        handlers are being used (for example when the crawler and the fuzzer use separate interaction handlers).

        :param with_logger: Add a logger to log operations
        :type with_logger: bool

        :param config: Custom configuration settings
        :type config: dict
        """
        self._mongo_helper = MongoHelper(for_batch)
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()
        self._states_collection = self._mongo_helper.get_states_collection()
        self._with_logger = with_logger
        if with_logger:
            self._logger = get_logger(name)
            self._logger.info('Ready')

    def generate(self) -> Request:
        """
        :raises NoMoreEndpoints: If the current state has no more unseen endpoints the scanner will rise this exception.

        :return: A Request to a previously unseen endpoint in the current state of the web app.
        :rtype: Request
        """
        current_state_id = self._mongo_helper.get_current_state_id()

        # Get the first entry that matches the query
        query = {'visited': False, 'allow_visit': True, 'clean': True, 'state_id': current_state_id}
        endpoint_query = self._endpoints_collection.find_one(query)

        if endpoint_query is None:
            raise NoMoreEndpoints("No more endpoints in mongo")

        # Mark selected endpoint as visited
        self._endpoints_collection.update_one(endpoint_query, {"$set": {"visited": True}})
        endpoint = Endpoint.from_dict(endpoint_query)

        # Generate request
        request = Request(endpoint)

        return request

    def execute(self, request: Request, save_interaction: bool = True, made_by_fuzzer: bool = False) -> Response:
        """
        Execute a :class:`Request` in the current state of the web app.

        :param request: The request that will be executed
        :type request: Request

        :param save_interaction: True if the interaction from the request should be added to the DB.
        :type save_interaction: bool

        :param made_by_fuzzer: True if the request was executed by an interaction handler of a fuzzer. This option
        will also flag the interaction added in the DB as one made by a fuzzer.
        :type made_by_fuzzer: bool

        :return: The response to the request
        :rtype: Response
        """
        current_state_id = self._mongo_helper.get_current_state_id()

        if self._with_logger:
            self._logger.info(request.endpoint)

        params = dict()
        for i in range(len(request.endpoint.parameters)):
            params[request.endpoint.parameters[i].name] = request.endpoint.parameters[i].value

        data = dict()
        for i in range(len(request.endpoint.data)):
            data[request.endpoint.data[i].name] = request.endpoint.data[i].value

        global session
        raw_response = session.request(
            method=request.endpoint.method,
            url=request.endpoint.url,
            headers=request.headers,
            params=params,
            data=data,
            timeout=50)

        response = Response(
            code=raw_response.status_code,
            data=raw_response.content.decode('utf-8'),
            headers=dict(raw_response.headers))

        interaction = Interaction(request=request,
                                  response=response,
                                  state_id=current_state_id,
                                  made_by_fuzzer=made_by_fuzzer)

        if save_interaction:
            self._mongo_helper.add_interaction(interaction)

        return response
