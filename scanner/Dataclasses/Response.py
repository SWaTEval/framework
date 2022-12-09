from dataclasses import dataclass, field
from typing import Any
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class Response:
    """
    A Response stores the raw data received upon a Request, along with the given response code.
    """

    code: int
    data: Any
    headers: dict = field(default_factory=dict)
