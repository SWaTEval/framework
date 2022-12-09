import json
from abc import abstractmethod
import socket

class ExternalScanner:
    """
    Interface for wrappers of  external scanners
    """

    @abstractmethod
    def scan(self, target_url, batch):
        pass

    @property
    @abstractmethod
    def logs(self):
        pass

    @abstractmethod
    def merge_logs(self, batch):
        pass