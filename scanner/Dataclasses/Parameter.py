from dataclasses import dataclass, field
from inspect import Parameter
from typing import Optional, Tuple
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass(frozen=True)
class Parameter:
    """
    A Parameter is an extending part of an Endpoint, which will take any arbitrary value at the time of a request.
    For convenience each Parameter can store a default value that will not be used in comparisons.
    """

    name: str
    value: str = field(default='')

    @staticmethod
    def parse_params(query) -> Tuple[Parameter, ...]:
        # TODO: Very simple parser, implemented without looking at the actual HTTP-specification. Might not always work.
        params = list()
        for part in query.split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                params.append(Parameter(name=k, value=v))
        return tuple(params)
