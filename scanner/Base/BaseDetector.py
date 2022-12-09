from abc import ABC, abstractmethod

from scanner.Base.BaseModule import BaseModule


class NoMoreUnprocessedInteractions(Exception):
    """
    Thrown when there are no more interactions for processing in the DB.
    """
    pass


class BaseDetector(BaseModule, ABC):
    """
    An abstract representation of a detector module, derivation of the :class:`BaseModule` class.
    """
    @abstractmethod
    def detect(self):
        """
        Detection logic is implemented here. This method gets invoked by the :meth:`run` method.
        """
        pass

    def run(self):
        self.detect()
