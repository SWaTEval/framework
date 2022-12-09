import json
import os
import shlex
import subprocess

from json import JSONDecodeError
from logging import Logger
from queue import Queue
from urllib.parse import urlparse, parse_qs

import redis
from bson import ObjectId
from omegaconf import OmegaConf
from pymongo.collection import Collection

from scanner.Base.BaseModule import BaseModule
from scanner.Crawling.Simple.SimpleInteractionHandler import get_session_object
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Interaction import Interaction
from scanner.Dataclasses.Parameter import Parameter
from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response
from scanner.ExternalScanners.WapitiWrapper.WapitiWrapper import WapitiWrapper
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class Wapiti(BaseModule):
    local_path = os.getcwd()
    _batch_name: str
    _endpoints_collection: Collection
    _states_collection: Collection
    _proxy_url: str
    _proxy_port: str
    _auto_start_proxy: str
    _endpoints_queue: Queue
    _max_scans_per_iteration: int
    _mongo_helper: MongoHelper
    _logger: Logger

    def __init__(self, for_batch: str):
        mongo_helper = MongoHelper(for_batch=for_batch)

        self._wapiti = WapitiWrapper()
        self._batch_name = for_batch

        # Create config parser
        config = OmegaConf.load('config.yaml')
        

        # Read redis config
        redis_config = config['redis']
        redis_host = redis_config['host']
        redis_port = redis_config['port']
        redis_db = redis_config['db']

        # Read proxy config
        proxy_config = config['proxy']
        proxy_scheme = proxy_config['scheme']
        proxy_host = proxy_config['host']
        proxy_port = proxy_config['port']
        proxy_auto_start = proxy_config['auto_start']

        self._proxy_port = str(proxy_port)
        self._proxy_url = proxy_scheme + "://" + proxy_host + ":" + proxy_port
        self._endpoints_collection = mongo_helper.get_endpoints_collection()
        self._states_collection = mongo_helper.get_states_collection()
        self._max_scans_per_iteration = 1
        self._auto_start_proxy = proxy_auto_start

        self._logger = get_logger("Wapiti")

        # Create a thread with a socket listener
        self._mongo_helper = MongoHelper(for_batch)

        pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db)
        self._redis = redis.Redis(connection_pool=pool)
        self.clear_redis_data()

    def scan(self, target_url: str):
        proxy_process = None
        if self._auto_start_proxy:
            proxy_command = "mitmdump -s request_extender.py --listen-port " + self._proxy_port
            proxy_process = subprocess.Popen(shlex.split(proxy_command),
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)

        session = get_session_object()
        cookies_dict = session.cookies.get_dict()
        headers_dict = dict(session.headers)
        cookies_dump = json.dumps(cookies_dict)
        headers_dump = json.dumps(headers_dict)

        self._redis.set('cookies', cookies_dump)
        self._redis.set('headers', headers_dump)

        command = 'wapiti -u ' + target_url + \
                  ' -p ' + self._proxy_url + \
                  ' -v 2' + \
                  ' -x http://wackopicko.docker/passcheck.php' + \
                  ' --scope url --flush-session --flush-attacks'

        subprocess.run(shlex.split(command),
                       # stdout=subprocess.DEVNULL,
                       # stderr=subprocess.DEVNULL
                       )

        if self._auto_start_proxy:
            proxy_process.kill()

    def run(self):
        current_state_id = self._mongo_helper.get_current_state_id()
        current_state = self._mongo_helper.get_current_state()
        if current_state.explored and not current_state.fuzzed:

            query_filter = {'clean': True,
                            'scanned': False,
                            'state_id': current_state_id}

            endpoints_left_for_scanning = self._endpoints_collection.count_documents(query_filter)

            if endpoints_left_for_scanning > 0:
                # Find clean endpoints that are not scanned in the current state
                endpoint_query = self._endpoints_collection.find_one(query_filter)

                endpoint = Endpoint.from_dict(endpoint_query)

                self._logger.info(f'Fuzzing {endpoint.url_with_params} in state {current_state_id}')

                # Scan the endpoint
                self.scan(target_url=endpoint.url_with_params)

                self.add_scanner_data(endpoint)

                self.clear_redis_data()

                # Update the endpoint in DB
                self._endpoints_collection.update_one(endpoint_query, {'$set': {'scanned': True}})

            else:
                self._states_collection.update_one({'_id': ObjectId(current_state_id)}, {'$set': {'fuzzed': True}})

    def add_scanner_data(self, endpoint: Endpoint):
        request_method = self._redis.get('request_method').decode('utf-8')

        request_content = self._redis.get('request_content').decode('utf-8')
        data_list = list()
        if len(request_content) > 0:
            try:
                data_params = json.loads(request_content)
                for name, value in data_params:
                    data_list.append(Parameter(name, value))
            except JSONDecodeError:
                params_list = request_content.split('&')
                for param in params_list:
                    name, value = param.split('=')
                    data_list.append(Parameter(name, value))

        response_headers = self._redis.get('response_headers').decode('utf-8')
        response_headers = json.loads(response_headers)

        response_content = self._redis.get('response_content').decode('utf-8')

        response_code = self._redis.get('response_code').decode('utf-8')
        response_code = int(response_code)

        request_url = self._redis.get('request_url').decode('utf-8')
        parsed_url = urlparse(request_url)
        parameter_dict = parse_qs(parsed_url.query)
        parameter_list = []
        for name, value in parameter_dict.items():
            parameter_list.append(Parameter(str(name), str(value[0])))

        # Remove problematic headers
        response_headers.pop('Content-Length', None)
        response_headers.pop('Keep-Alive', None)
        response_headers.pop('Connection', None)
        response_headers.pop('Transfer-Encoding', None)

        state_id = self._mongo_helper.get_current_state_id()

        fuzzy_endpoint = Endpoint(scheme=endpoint.scheme,
                                  host=endpoint.host,
                                  path=endpoint.path,
                                  state_id=endpoint.state_id,
                                  found_at=endpoint.found_at,
                                  from_interaction_id=endpoint.from_interaction_id,
                                  parameters=tuple(parameter_list),
                                  data=tuple(data_list),
                                  method=request_method, )

        request = Request(endpoint=fuzzy_endpoint,
                          headers=response_headers)

        response = Response(code=response_code,
                            headers=response_headers,
                            data=response_content)

        interaction = Interaction(request=request,
                                  response=response,
                                  state_id=state_id,
                                  endpoints_processed=False,
                                  clustering_processed=False,
                                  made_by_fuzzer=True)

        self._mongo_helper.add_interaction(interaction)

    def clear_redis_data(self):
        self._redis.delete('request_url')
        self._redis.delete('request_method')
        self._redis.delete('request_content')

        self._redis.delete('response_headers')
        self._redis.delete('response_content')
        self._redis.delete('response_code')
