import os
import re
from enum import Enum
from functools import lru_cache, total_ordering
import logging
import requests
import urllib

from retry import retry

from cmat.trait_mapping.ontology_uri import OntologyUri
from cmat.trait_mapping.utils import json_request, ServerError

OLS_BASE_URL = 'https://www.ebi.ac.uk/ols4/api'

logger = logging.getLogger(__package__)


def build_ols_query(ontology_uri: str) -> str:
    """Build a url to query OLS for a given ontology uri."""
    return "{}/terms?iri={}".format(OLS_BASE_URL, ontology_uri)


@lru_cache(maxsize=16384)
def get_label_and_synonyms_from_ols(ontology_uri: str) -> str:
    """
    Using provided ontology URI, build an OLS URL with which to make a request to find the term label for this URI.

    :param ontology_uri: A URI for a term in an ontology.
    :return: Term label for the ontology URI provided in the parameters.
    """
    url = build_ols_query(ontology_uri)
    json_response = json_request(url)

    if not json_response:
        return None

    # If the '_embedded' section is missing from the response, it means that the term is not found in OLS
    if '_embedded' not in json_response:
        if '/medgen/' not in url and '/omim/' not in url:
            logger.warning('OLS queried OK but did not return any results for URL {}'.format(url))
        return None

    # Go through all terms found by the requested identifier and try to find the one where the _identifier_ and the
    # _term_ come from the same ontology (marked by a special flag). Example of such a situation would be a MONDO term
    # in the MONDO ontology. Example of a reverse situation is a MONDO term in EFO ontology (being *imported* into it
    # at some point).
    for term in json_response["_embedded"]["terms"]:
        if term["is_defining_ontology"]:
            return term["label"], term["synonyms"]

    if '/medgen/' not in url and '/omim/' not in url:
        logger.warning('OLS queried OK, but there is no defining ontology in its results for URL {}'.format(url))
    return None


def double_encode_uri(uri: str) -> str:
    """Double encode a given uri."""
    return urllib.parse.quote(urllib.parse.quote(uri, safe=""), safe="")


@retry(exceptions=(ConnectionError, ServerError), logger=logger, tries=8, delay=2, backoff=1.2, jitter=(1, 3))
def ols_ontology_query(uri: str, ontology: str = 'EFO') -> requests.Response:
    """
    Query target ontology using OLS for a given ontology uri, returning the response from the request.

    :param uri: Ontology uri to use in querying target ontology using OLS
    :param ontology: ID of target ontology to query (default EFO)
    :return: Response from OLS
    """
    double_encoded_uri = double_encode_uri(uri)
    response = requests.get(f"{OLS_BASE_URL}/ontologies/{ontology}/terms/{double_encoded_uri}")
    if 500 <= response.status_code < 600:
        raise ServerError
    return response


@lru_cache(maxsize=16384)
def is_current_and_in_ontology(uri: str, ontology: str = 'EFO') -> bool:
    """
    Checks whether given ontology uri is a valid and non-obsolete term in target ontology.

    :param uri: Ontology uri to use in querying target ontology using OLS
    :param ontology: ID of target ontology to query (default EFO)
    :return: Boolean value, true if ontology uri is valid and non-obsolete term in target ontology
    """
    response = ols_ontology_query(uri, ontology)
    if response.status_code != 200:
        return False
    response_json = response.json()
    return not response_json["is_obsolete"]


@lru_cache(maxsize=16384)
def is_in_ontology(uri: str, ontology: str = 'EFO') -> bool:
    """
    Checks whether given ontology uri is a valid term in target ontology.

    :param uri: Ontology uri to use in querying target ontology using OLS
    :param ontology: ID of target ontology to query (default EFO)
    :return: Boolean value, true if ontology uri is valid term in target ontology
    """
    response = ols_ontology_query(uri, ontology)
    return response.status_code == 200


@lru_cache(maxsize=16384)
def get_replacement_term(uri: str, ontology: str = 'EFO') -> str:
    """
    Finds replacement term in target ontology (if present) for the given ontology uri.

    :param uri: Ontology uri to use in querying target ontology using OLS
    :param ontology: ID of target ontology to query (default EFO)
    :return: Replacement term URI or empty string if not obsolete
    """
    response = ols_ontology_query(uri, ontology)
    if response.status_code != 200:
        return ""
    response_json = response.json()
    if response_json["term_replaced_by"] is not None:
        replacement_uri = response_json["term_replaced_by"]
        if not replacement_uri.startswith('http'):
            try:
                # Attempt to correct the most common weirdness found in this field - MONDO:0020783 or HP_0045074
                db, iden = re.split(':|_', replacement_uri)
                replacement_uri = OntologyUri(iden, db.lower()).uri
            except:
                logger.warning(f'Could not normalise replacement term: {replacement_uri}')
        return replacement_uri
    return ""


@lru_cache(maxsize=16384)
@retry(exceptions=(ConnectionError, requests.RequestException), tries=4, delay=2, backoff=1.2, jitter=(1, 3))
def get_uri_from_exact_match(text, ontology='EFO'):
    """
    Finds URI from target ontology for a given text based on exact string match.

    :param text: String to search for
    :param ontology: ID of target ontology to query (default EFO)
    :return: URI of matching term or None if not found
    """
    search_url = os.path.join(OLS_BASE_URL, f'search?ontology={ontology}&q={text}&queryFields=label&exact=true')
    response = requests.get(search_url)
    response.raise_for_status()
    data = response.json()
    if 'response' in data:
        results = data['response']['docs']
        candidates = set()
        for result in results:
            # Check that we've found the term exactly (strict case-insensitive string match)
            if result['label'].lower() == text.lower():
                candidates.add(result['iri'])
        # Only return a result if we can find it unambiguously
        if len(candidates) == 1:
            return candidates.pop()
    logger.warning(f'Could not find an IRI for {text}')
    return None


class MatchType(Enum):
    EXACT_MATCH_LABEL = 0
    EXACT_MATCH_SYNONYM = 1
    CONTAINED_MATCH_LABEL = 2
    CONTAINED_MATCH_SYNONYM = 3
    TOKEN_MATCH_LABEL = 4
    TOKEN_MATCH_SYNONYM = 5
    NO_MATCH = 6

    def __str__(self):
        return self.name


class MappingSource(Enum):
    # TODO generalise to target/preferred ontologies?
    EFO_CURRENT = 0
    EFO_OBSOLETE = 1
    MONDO_HP_NOT_EFO = 2
    NOT_MONDO_HP_EFO = 3

    def __str__(self):
        return self.name


@total_ordering
class OlsResult:
    """Representation of one ontology term coming from OLS"""

    def __init__(self, uri, label, full_exact_match, contained_match, token_match, in_target_ontology,
                 in_preferred_ontology, is_current):
        self.uri = uri
        self.label = label
        self.full_exact_match = full_exact_match
        self.contained_match = contained_match
        self.token_match = token_match
        self.in_target_ontology = in_target_ontology
        self.in_preferred_ontology = in_preferred_ontology
        self.is_current = is_current

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.uri == other.uri and self.label == other.label

    def __hash__(self):
        return hash((self.uri, self.label))

    def __gt__(self, other):
        # Larger means better mapping
        # In general, full exact matches > contained matches > token matches,
        # and target ontology > preferred ontologies > neither
        if self.full_exact_match:
            if other.full_exact_match:
                return self.ontology_rank() > other.ontology_rank()
            else:
                return True
        if self.contained_match:
            if other.full_exact_match:
                return False
            if other.contained_match:
                return self.ontology_rank() > other.ontology_rank()
            else:
                return True
        if self.token_match:
            if other.full_exact_match:
                return False
            if other.contained_match:
                return False
            if other.token_match:
                return self.ontology_rank() > other.ontology_rank()
            else:
                return True

    def ontology_rank(self):
        if self.in_target_ontology:
            return 2
        if self.in_preferred_ontology:
            return 1
        return 0

    def get_match_type(self):
        if self.full_exact_match:
            if 'label' in self.full_exact_match:
                return MatchType.EXACT_MATCH_LABEL
            if 'synonym' in self.full_exact_match:
                return MatchType.EXACT_MATCH_SYNONYM
        if self.contained_match:
            if 'label' in self.contained_match:
                return MatchType.CONTAINED_MATCH_LABEL
            if 'synonym' in self.contained_match:
                return MatchType.CONTAINED_MATCH_SYNONYM
        if self.token_match:
            if 'label' in self.token_match:
                return MatchType.TOKEN_MATCH_LABEL
            if 'synonym' in self.token_match:
                return MatchType.TOKEN_MATCH_SYNONYM
        return MatchType.NO_MATCH

    def get_mapping_source(self):
        if self.in_target_ontology:
            return MappingSource.EFO_CURRENT if self.is_current else MappingSource.EFO_OBSOLETE
        if self.in_preferred_ontology:
            return MappingSource.MONDO_HP_NOT_EFO
        return MappingSource.NOT_MONDO_HP_EFO


def get_fields_with_match(search_term, query_fields, result_json):
    search_term = search_term.lower().strip()
    full_exact_match = []
    contained_match = []
    token_match = []
    for field in query_fields:
        if field in result_json:
            if isinstance(result_json[field], str):
                if  search_term == result_json[field].lower().strip():
                    full_exact_match.append(field)
                elif search_term in result_json[field].lower():
                    contained_match.append(field)
                else:
                    token_match.append(field)
            if isinstance(result_json[field], list):
                if [element for element in result_json[field] if search_term == element.lower().strip()]:
                    full_exact_match.append(field)
                elif [element for element in result_json[field] if search_term in element.lower()]:
                    contained_match.append(field)
                else:
                    token_match.append(field)
    return full_exact_match, contained_match, token_match


def get_is_in_ontologies(uri, target_ontology, preferred_ontologies):
    in_target_ontology = is_in_ontology(uri, target_ontology)
    in_preferred_ontology = False
    for ontology in preferred_ontologies:
        if is_in_ontology(uri, ontology):
            in_preferred_ontology = True
            break
    return in_target_ontology, in_preferred_ontology


def get_ols_results(term, ontologies, query_fields, field_list, target_ontology='EFO'):
    """Returns a list of OlsResults."""
    if ontologies is None or query_fields is None or field_list is None:
        return []
    search_url = OLS_BASE_URL + "/search"
    params = {
        'q': term,
        'exact': 'false',
        'obsoletes': 'false',
        'ontologies': ontologies,
        'queryFields': query_fields,
        'fieldList': field_list
    }
    preferred_ontologies = set(ontologies.split(','))
    if target_ontology.lower() in preferred_ontologies:
        preferred_ontologies.remove(target_ontology.lower())

    try:
        results = json_request(search_url, params=params)
        if results['response']['numFound'] > 0:
            search_results = set()

            for result in results['response']['docs']:
                uri = result.get('iri')
                label = result.get('label')
                full_exact_match, contained_match, token_match = get_fields_with_match(uri, query_fields.split(','),
                                                                                       result)
                in_target_ontology, in_preferred_ontology = get_is_in_ontologies(uri, target_ontology,
                                                                                 preferred_ontologies)
                # Query includes obsoletes=false
                is_current = True if in_target_ontology else False
                search_results.add(OlsResult(uri, label, full_exact_match, contained_match, token_match,
                                             in_target_ontology, in_preferred_ontology, is_current))
            return list(search_results)
        else:
            return []

    except requests.RequestException as e:
        logger.warning(f"Error querying OLS4: {e}")
        return []
