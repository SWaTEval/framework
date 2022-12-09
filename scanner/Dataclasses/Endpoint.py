from dataclasses import dataclass, field
import time
from typing import Tuple, Any
from scanner.Dataclasses.Parameter import Parameter
from dataclasses_json import dataclass_json
import tlsh

from scanner.Utilities.Util import get_hash_padding, get_config


@dataclass_json
@dataclass
class Endpoint:
    """
    An Endpoint stores all the required information to construct a Request.
    """

    host: str
    path: str
    state_id: Any
    from_interaction_id: Any
    found_at: Tuple[str, ...] = ()
    parameters: Tuple[Parameter, ...] = ()
    data: Tuple[Parameter, ...] = ()
    scheme: str = 'http'
    method: str = "GET"
    clustering_processed: bool = False
    visited: bool = False
    scanned: bool = False
    clean: bool = False
    is_reset: bool = False
    hash: str = field(init=False)
    created_at: int = field(init=False)

    @property
    def url(self) -> str:
        """
        :return: The endpoint as an url without parameters
        :rtype: str
        """
        return f"{self.scheme}://{self.host}{self.path}"

    @property
    def parameters_as_string(self) -> str:
        """
        :return: The parameters of the endpoint as an url query string
        :rtype: str
        """
        parameter_list = list(self.parameters)
        data_list = list(self.data)

        # Prepare url query params
        parameter_string = "?"
        for parameter in parameter_list:
            parameter_string += f'{parameter.name}={parameter.value}&'

        if len(parameter_string) == 1:
            parameter_string = ""
        else:
            parameter_string = parameter_string[:-1]

        # Prepare form data params
        data_string = '['
        for parameter in data_list:
            data_string += f'({parameter.name}={parameter.value}),'

        if len(data_string) == 1:
            data_string = ''
        else:
            data_string = data_string[:-1]
            data_string += ']'

        output_string = parameter_string + ' ' + data_string
        return output_string

    @property
    def url_with_params(self) -> str:
        """
        :return: The endpoint as an url with parameters
        :rtype: str
        """
        query_params = ""
        if len(self.parameters) > 0:
            query_params = "?"
            for idx, parameter in enumerate(self.parameters):
                if idx > 0:
                    query_params += '&'

                key = parameter.name
                value = "" if parameter.value is None else parameter.value
                query_params += key + '=' + value

        return f"{self.scheme}://{self.host}{self.path}{query_params}"

    def _generate_hash(self) -> str:
        '''
        :return: Generates the TLSH representation of an Endpoint
        :rtype: str
        '''
        param_list = list(self.parameters)
        param_str = ""
        for param in param_list:
            param_str += param.to_json()

        found_at_list = list(self.found_at)
        found_at_str = ""
        for entry in found_at_list:
            found_at_str += str(entry)

        endpoint_string = self.method + \
                          self.scheme + \
                          self.path + \
                          found_at_str + \
                          param_str

        # This ensures that tlsh will have enough data to generate a hash
        config = get_config()
        random_seed = config['random_seed']
        hash_padding = get_hash_padding(random_seed)
        data_bytes = (hash_padding + endpoint_string).encode()
        hash = tlsh.hash(data_bytes)
        return hash

    def __post_init__(self):
        timestamp_ms = int(round(time.time() * 1000))
        self.hash = self._generate_hash()
        self.created_at = timestamp_ms

    def __str__(self):
        return f'{self.method} {self.url_with_params}'


@dataclass_json
@dataclass
class EndpointClusteringInfo:
    """
    Contains clustering information for a specific endpoint.
    """
    host: str
    scheme: str
    path: str
    method: str
    state_id: Any
    cluster_count: int
