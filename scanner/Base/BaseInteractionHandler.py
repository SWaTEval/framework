from abc import abstractmethod, ABC

from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response


class NoMoreEndpoints(Exception):
    """
    Thrown when there are no more endpoints matching a selection criterion in the DB.
    """
    pass


class BaseInteractionHandler(ABC):
    """
    An abstract representation of the interaction handler.
    """

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def generate(self) -> Request:
        """
        This method is used for request generation. Custom logic is used to implement additional functionality, as for
        example automatic endpoint selection, state selection, etc.
        """
        pass

    @abstractmethod
    def execute(self, request: Request, save_interaction: bool) -> Response:
        """
        This method is used for request execution. Custom logic is used to implement additional functionality.
        """
        pass
