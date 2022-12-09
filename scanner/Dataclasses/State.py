import time
from typing import List

import tlsh
from dataclasses_json import dataclass_json
from dataclasses import dataclass, field

from scanner.Utilities.Util import random_string


class NoStateMarkedAsCurrent(Exception):
    """
    Thrown when there is no state in the DB marked as current.
    """
    pass

@dataclass_json
@dataclass
class StateReachabilityInfo:
    """
        Contains State reachability data.
    """
    from_state_id: str
    caused_by_interaction_id: str

@dataclass_json
@dataclass
class State:
    """
    Contains the data of a detected state
    """

    previous_state_id: str
    caused_by_interaction_id: str
    revisits: int = 0
    reachable_from: List = field(default_factory=list)
    current: bool = False
    explored: bool = False
    collapsed: bool = False
    fuzzed: bool = False
    initial: bool = False
    hash: str = field(init=False)
    created_at: int = field(init=False)

    def __post_init__(self):
        timestamp_ms = int(round(time.time() * 1000))
        self.created_at = timestamp_ms

        # Generate an initial hash which will be updated by the state collapse detector
        self.hash = State.generate_random_hash()

    @staticmethod
    def generate_random_hash() -> str:
        """
        Generates a random hash for a :class:`State` when there is not enough data for a real one.

        This may seem contra-intuitive, but works, because states are checked for similarity via the hash.
        We want to consider only states, that have enough exploration data when running the state collapsing pipeline
        and this method ensures that not properly explored states won't be collapsed if they seem alike in the beginning.
        (i.e. this ensures lower false positive detections in the early exploration process.)
        """
        # Generate an initial hash which will be updated by the state collapse detector
        data_bytes = random_string(200).encode()
        random_hash = tlsh.hash(data_bytes)
        return random_hash
