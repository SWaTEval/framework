
from itertools import chain
from typing import Iterable, Dict, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from ordered_set import OrderedSet

from scanner.Base.BaseDetector import NoMoreUnprocessedInteractions, BaseDetector
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.Parameter import Parameter
from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper


class EndpointExtractor(BaseDetector):
    def __init__(self,
                 for_batch: str,
                 ignore_endpoints: List[Endpoint] = None,
                 restrict_host: bool = True,
                 config=None):
        """
        The most basic version of an :class:`Endpoint` detector. Gets the job done withouth any complex operation, but
        simply by parsing the body of a :class:`Response` in an :class:`Interaction` and looking for links, forms and redirects.

        :param for_batch: Name of the batch in the DB where endpoints are going to be searched in
        :type for_batch: str

        :param ignore_endpoints: List of endpoints to skip adding when found
        :type ignore_endpoints: List[Endpoint]

        :param config: Pass a parsed `config.yaml`
        :type config: Dict

        :param restrict_host: Add only endpoints from the current host address or also endpoints outside the current address scope
        :type restrict_host: bool
        """

        self._ignore_endpoints = ignore_endpoints
        self._for_batch = for_batch
        self._logger = get_logger("Endpoint Extractor")

        # MongoDB Stuff
        self._mongo_helper = MongoHelper(self._for_batch)
        self._interactions_collection = self._mongo_helper.get_interactions_collection()
        self._endpoints_collection = self._mongo_helper.get_endpoints_collection()

        if config:
            ed_section = config['endpoint_extractor']

            self._restrict_host = ed_section['restrict_host']
        else:
            self._restrict_host = restrict_host

        self._logger.info('Ready')
        self._logger.info(f'Restrict detection to host: {restrict_host}')

    def detect(self):
        """
        Searches for endpoints in all new unprocessed interactions by checking the request body and looking for links,
        forms and redirects
        """

        # Query unprocessed interactions
        unprocessed_interactions_query = self._interactions_collection.find({'endpoints_processed': False})

        if unprocessed_interactions_query is None:
            raise NoMoreUnprocessedInteractions("All interactions in mongo are marked as processed")

        for unprocessed_interaction_query in unprocessed_interactions_query:
            self._current_interaction_id = str(unprocessed_interaction_query['_id'])

            # Get endpoints from interaction
            extracted_endpoints = self.find_endpoints(unprocessed_interaction_query)

            # Remove ignored endpoints
            for endpoint_to_ignore in self._ignore_endpoints:
                for endpoint_found in extracted_endpoints:
                    if endpoint_to_ignore.path == endpoint_found['path']:
                        extracted_endpoints.remove(endpoint_found)

            # Mark interaction as processed
            self._interactions_collection.find_one_and_update(unprocessed_interaction_query,
                                                              {'$set': {'endpoints_processed': True}})

            self._endpoints_collection.insert_many(extracted_endpoints)

            self._logger.info(f'Processed interaction {unprocessed_interaction_query["_id"]}')
            self._logger.info(f'Added {len(extracted_endpoints)} endpoints')

    def find_endpoints(self, interaction_query: dict) -> List[dict]:
        """
        Find new endpoints in the response of an interaction

        :param interaction_query: The interaction where the response is stored
        :type interaction_query: dict (non casted :class:`Interaction`)

        :return: List of new endpoints
        :rtype: List[dict] (dict is a non cast :class:`Interaction`)
        """

        request = Request.from_dict(interaction_query['request'])
        response = Response.from_dict(interaction_query['response'])
        in_state_id = interaction_query['state_id']

        relative_to = request.endpoint
        soup = BeautifulSoup(response.data, features="html.parser")

        new_endpoints: List[dict] = []

        redirects = self.find_redirects(response.code, response.headers, relative_to, in_state_id)
        for endpoint in redirects:
            if endpoint not in self._ignore_endpoints:
                new_endpoints.append(endpoint.to_dict())

        links = self.find_links(soup, relative_to, in_state_id)
        for endpoint in links:
            if endpoint not in self._ignore_endpoints:
                new_endpoints.append(endpoint.to_dict())

        forms = self.find_forms(soup, relative_to, in_state_id)
        for endpoint in forms:
            if endpoint not in self._ignore_endpoints:
                new_endpoints.append(endpoint.to_dict())

        return new_endpoints

    def find_links(self, soup: BeautifulSoup, relative_to: Endpoint, in_state_id: str) -> Iterable[Endpoint]:
        """
        Find links stored in html body data

        :param soup: BS parsed html body
        :type soup: BeautifulSoup

        :param relative_to: Host to which the searched links are going to be restricted
        :type relative_to: Endpoint

        :param in_state_id: State id in which the links are currently being searched
        :type in_state_id: str

        :return: List of new endpoints
        :rtype: List[dict] (dict is a non cast :class:`Interaction`)
        """

        for anchor in soup.find_all('a'):
            target = self.resolve(anchor.get('href', ''), relative_to, self._restrict_host)
            if not target:
                continue

            yield Endpoint(
                method='GET',
                host=target.netloc,
                scheme=target.scheme,
                path=target.path,
                parameters=Parameter.parse_params(target.query),
                found_at=self.path_of(anchor),
                state_id=in_state_id,
                from_interaction_id=self._current_interaction_id,
            )

    def find_forms(self, soup: BeautifulSoup, relative_to: Endpoint, in_state_id: str) -> Iterable[Endpoint]:
        """
        Find forms stored in html body data

        :param soup: BS parsed html body
        :type soup: BeautifulSoup

        :param relative_to: Host to which the searched links are going to be restricted
        :type relative_to: Endpoint

        :param in_state_id: State id in which the links are currently being searched
        :type in_state_id: str

        :return: List of new endpoints
        :rtype: List[dict] (dict is a non cast :class:`Interaction`)
        """

        for form in soup.find_all('form'):
            target = self.resolve(form.get('action'), relative_to, self._restrict_host)

            if not target:
                continue

            parameters = OrderedSet()

            for field in chain(form.find_all('input'), form.find_all('button')):
                if field.has_attr('name'):
                    name = field.get('name')
                    value = field.get('value')

                    if value is None:
                        value = ""

                    parameters.add(Parameter(name, value))

            method = form.get('method').upper()
            host = target.netloc
            scheme = target.scheme
            path = target.path
            parameters = tuple(parameters)
            found_at = self.path_of(form)

            # The RFC7231 standard specifies that GET requests can have a body, but it has no semantic meaning
            # That's why it's assumed that forms with GET method send the parameters as a query string in the URL
            # Whereas forms with POST method send the parameters as a body string
            # For more info refer to the specs:
            # https://datatracker.ietf.org/doc/html/rfc7231#section-4.3.1
            if method == 'GET':
                yield Endpoint(
                    method=method,
                    host=host,
                    scheme=scheme,
                    path=path,
                    parameters=tuple(parameters),
                    found_at=found_at,
                    state_id=in_state_id,
                    from_interaction_id=self._current_interaction_id,
                )
            else:
                yield Endpoint(
                    method=method,
                    host=host,
                    scheme=scheme,
                    path=path,
                    data=tuple(parameters),
                    found_at=found_at,
                    state_id=in_state_id,
                    from_interaction_id=self._current_interaction_id
                )

    def find_redirects(self, code: int, headers: Dict, relative_to: Endpoint, in_state_id: str) -> Iterable[Endpoint]:
        """
        Find redirects stored in the body data

        :param code: Response code
        :type code: int

        :param relative_to: Host to which the searched links are going to be restricted
        :type relative_to: Endpoint

        :param in_state_id: State id in which the links are currently being searched
        :type in_state_id: str

        :return: List of new endpoints
        :rtype: List[dict] (dict is a non cast :class:`Interaction`)
        """

        if 'Location' in headers:
            redirect = self.resolve(headers.get('Location'), relative_to, self._restrict_host)
            if not redirect:
                return
            yield Endpoint(
                method='GET',
                host=redirect.netloc,
                scheme=redirect.scheme,
                path=redirect.path,
                parameters=Parameter.parse_params(redirect.query),
                found_at=('[header]', str(code)),
                state_id=in_state_id,
                from_interaction_id=self._current_interaction_id,
            )

    @staticmethod
    def resolve(url: str, relative_to: Endpoint, restrict_host: bool) -> tuple:
        """
        Decide if an url should be skipped or added based

        :param url: Url that will be checked
        :type url: str

        :param relative_to: Host to which the searched links are going to be restricted
        :type relative_to: Endpoint

        :param restrict_host: Decides if the host should be checked or directly added
        :type in_state_id: bool

        :return: When propperly resolved a 6-tuple: (scheme, netloc, path, params, query, fragment) or None
        :rtype: tuple
        """

        target = urlparse(urljoin(relative_to.url, url))
        if restrict_host and target.netloc != relative_to.host:
            return None
        else:
            return target

    @staticmethod
    def path_of(anchor):
        return tuple(reversed([p.name for p in anchor.parents]))
