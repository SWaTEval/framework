import json
from dataclasses import dataclass, field
import time
from typing import Any

from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response
from dataclasses_json import dataclass_json
from bs4 import BeautifulSoup
import tlsh

from scanner.Utilities.Util import get_hash_padding, get_config


class NonExistingHashDataMethod(Exception):
    """
    Thrown when hash data method is not existing.
    """
    pass


@dataclass_json
@dataclass
class Interaction:
    """
    Contains a pair of Request and Response. Additionally, has flags for the processing status in the pipeline.
    """
    request: Request
    response: Response
    state_id: Any
    endpoints_processed: bool = False
    clustering_processed: bool = False
    made_by_fuzzer: bool = False
    hash: str = field(init=False)
    created_at: int = field(init=False)

    @staticmethod
    def generate_hash(request: Request, response: Response, method="links-only") -> str:
        """
        Generates an interaction hash using the :class:`Request` and :class:`Response` data.

        :param request: The request of the interaction
        :type: Request

        :param response: The response of the interaction
        :type: Response

        :param method: The method used to generate the hash (can be 'links-only', 'links-with-params' or 'whole-response')
        :type: str

        :return: The TLSH representation of the interaction
        :rtype: str
        """

        if method == 'links-only':
            interaction_string = Interaction._generate_data_for_hash_from_links(request, response)
        elif method == 'links-with-params':
            interaction_string = Interaction._generate_data_for_hash_from_links_and_parameters(request, response)
        elif method == 'whole-response':
            interaction_string = Interaction._generate_data_for_hash_from_whole_response(request, response)
        else:
            raise NonExistingHashDataMethod(
                f'No method {method} exists. Please select one of the following: whole-response, links-with-params, links-only')

        # This ensures that tlsh will have enough data to generate a hash'
        config = get_config()
        random_seed = config['random_seed']
        hash_padding = get_hash_padding(random_seed)
        data_bytes = (hash_padding + interaction_string).encode()
        hash = tlsh.hash(data_bytes)
        return hash

    @staticmethod
    def _generate_data_for_hash_from_whole_response(request: Request, response: Response) -> str:
        """
        Generates a hash using all data contained in the response body

        :param request: The request of the interaction
        :type: Request

        :param response: The response of the interaction
        :type: Response

        :return: The TLSH representation of the interaction
        :rtype: str
        """

        param_list = list(request.endpoint.parameters)
        param_str = ""
        for param in param_list:
            param_str += param.to_json()

        # Info: Parameter values are not added to the hash, because we want to get the same hash output when fuzzing
        # an endpoint with different parameters and getting the same output in the request.
        interaction_string = request.endpoint.method + \
                             request.endpoint.scheme + \
                             request.endpoint.path + \
                             param_str + \
                             json.dumps(request.headers) + \
                             str(response.code) + \
                             response.data

        # request.endpoint.url  - contains a nondeterministic port

        return interaction_string

    @staticmethod
    def _generate_data_for_hash_from_links(request: Request, response: Response) -> str:
        """
        Generates a hash using only the links without parameters contained in the response body

        :param request: The request of the interaction
        :type: Request

        :param response: The response of the interaction
        :type: Response

        :return: The TLSH representation of the interaction
        :rtype: str
        """

        soup = BeautifulSoup(response.data, features="html.parser")

        anchors = [str(a) for a in soup.find_all('a')]
        forms = [str(form) for form in soup.find_all('form')]

        anchors_str = ''.join(anchors)
        forms_str = ''.join(forms)

        interaction_string = request.endpoint.method + \
                             request.endpoint.scheme + \
                             request.endpoint.path + \
                             str(response.code) + \
                             anchors_str + \
                             forms_str
        # request.endpoint.host  - contains non deterministic app port
        return interaction_string

    @staticmethod
    def _generate_data_for_hash_from_links_and_parameters(request: Request, response: Response) -> str:
        """
        Generates a hash using all the links with parameters contained in the response body

        :param request: The request of the interaction
        :type: Reques

        :param response: The response of the interaction
        :type: Respons

        :return: The TLSH representation of the interaction
        :rtype: str
        """

        soup = BeautifulSoup(response.data, features="html.parser")
        param_list = list(request.endpoint.parameters)
        param_str = ""
        for param in param_list:
            param_str += param.to_json()

        anchors = [str(a) for a in soup.find_all('a')]
        forms = [str(form) for form in soup.find_all('form')]

        anchors_str = ''.join(anchors)
        forms_str = ''.join(forms)

        interaction_string = request.endpoint.method + \
                             request.endpoint.scheme + \
                             request.endpoint.path + \
                             param_str + \
                             json.dumps(request.headers) + \
                             str(response.code) + \
                             anchors_str + \
                             forms_str
        # request.endpoint.url - contains nondeterministic app port
        return interaction_string

    def __post_init__(self):
        timestamp_ms = int(round(time.time() * 1000))
        self.hash = self.generate_hash(self.request, self.response)
        self.created_at = timestamp_ms


@dataclass_json
@dataclass
class InteractionClusteringInfo:
    """
    Contains clustering information for a specific interaction.
    """
    request_endpoint_host: str
    request_endpoint_scheme: str
    request_endpoint_path: str
    request_endpoint_method: str
    state_id: Any
    cluster_count: int
