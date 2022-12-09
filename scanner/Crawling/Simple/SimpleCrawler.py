from logging import Logger
from queue import LifoQueue

from scanner.Base.BaseCrawler import BaseCrawler
from scanner.Base.BaseInteractionHandler import NoMoreEndpoints
from scanner.Crawling.Simple.SimpleInteractionHandler import SimpleInteractionHandler
from scanner.Crawling.Simple.SimpleStateNavigator import SimpleStateNavigator, NoMoreStatesToExplore
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class SimpleCrawler(BaseCrawler):
    """
    This crawler has integrated  :class:`SimpleStateNavigator` that selects the next suitable state for crawling and
    creates a list of interactions that put the web app in it, and a :class:`SimpleInteractionHandler`
    that executes the list of interactions and generates a new interaction with the web app using
    an endpoint that was not previously visited.
    """

    def __init__(self, for_batch: str, config=None):
        """
        :param for_batch: Name of the batch containing information about the current app scan in the DB
        :type for_batch: str

        :param config: Custom configuration settings
        :type config: dict
        """
        self._mongo_helper = MongoHelper(for_batch)
        self._interaction_handler = SimpleInteractionHandler(for_batch=for_batch, config=config)
        self._state_navigator = SimpleStateNavigator(for_batch=for_batch, config=config)
        self._logger = get_logger("Crawler")
        self._logger.info('Ready')

    def crawl(self):
        """
        Find a non explored state and visit a new endpoint.
        """
        # Find a suitable state
        try:
            request_queue: LifoQueue = self._state_navigator.run()
        except NoMoreStatesToExplore:
            self._logger.info("Finished")
            return "crawling converged"

        # Navigate to the state
        nav_interaction_count = 0
        self._logger.info("Executing navigation queue")
        while not request_queue.empty():
            nav_interaction_count += 1
            self._logger.info(f'Navigation Interaction {nav_interaction_count}')
            request = request_queue.get()
            self._interaction_handler.execute(request, save_interaction=False)
        self._logger.info("State navigation done")

        # Crawl the state
        try:
            request = self._interaction_handler.generate()
            self._interaction_handler.execute(request, save_interaction=True)
        except NoMoreEndpoints:
            current_state_id = self._mongo_helper.get_current_state_id()
            self._logger.info(f'No more endpoints to visit for state {current_state_id}')
