from abc import ABC, abstractmethod


class BaseModule(ABC):
    """
    The most granular class unit of the project. It is used as an interface for the :class:`Work` classes
    """

    @abstractmethod
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def run(self):
        """
        The interface method that gets invoked by the workers created with the :class:`Work` classes.
        Each derivative of the :class:`BaseModule` class implements its own functionality that is called with
        the run() method.
        """

        pass
