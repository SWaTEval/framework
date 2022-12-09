from abc import abstractmethod, ABC

from scanner.Base.BaseModule import BaseModule


class BaseCrawler(BaseModule, ABC):
    """
    An abstract representation of the crawler, derivation of the :class:`BaseModule` class.
    """

    @abstractmethod
    def crawl(self):
        """
        Crawling logic is implemented here. This method gets invoked by the :meth:`run` method.
        """
        pass

    def run(self):
        return self.crawl()
