from dataclasses import dataclass, field
from typing import Any
from scanner.Dataclasses.Endpoint import Endpoint
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class Request:
    """
    A Request is the complete set of information (Endpoint, Parameter values) that can be sent to a web application.
    """

    endpoint: Endpoint
    headers: dict = field(default_factory=dict)
