import re
from functools import lru_cache
import logging
import requests
import urllib

from retry import retry

from cmat.trait_mapping.ontology_uri import OntologyUri
from cmat.trait_mapping.utils import json_request, ServerError

OLS_BASE_URL = 'https://www.ebi.ac.uk/ols4/api/v2'
EXACT_SYNONYM_KEY = 'http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'
REPLACEMENT_KEY = 'http://purl.obolibrary.org/obo/IAO_0100001'

logger = logging.getLogger(__package__)


def build_ols_query(ontology_uri: str, include_obsoletes: bool = False) -> str:
    """Build a url to query OLS for a given ontology uri."""
    query_url = f'{OLS_BASE_URL}/classes?iri={ontology_uri}'
    if include_obsoletes:
        query_url = f'{query_url}&includeObsoleteEntities=true'
    return query_url


@lru_cache(maxsize=16384)
def get_label_and_synonyms_from_ols(ontology_uri: str) -> tuple:
    """
    Using provided ontology URI, build an OLS URL with which to make a request to find the term label and synonyms for this URI.

    :param ontology_uri: A URI for a term in an ontology.
    :return: Term label for the ontology URI provided in the parameters and set of synonymes.
    """
    url = build_ols_query(ontology_uri, include_obsoletes=True)
    json_response = json_request(url)

    if not json_response:
        return '', set()

    # If the 'elements' section is missing from the response, it means that the term is not found in OLS
    if 'elements' not in json_response:
        if '/medgen/' not in url and '/omim/' not in url:
            logger.warning('OLS queried OK but did not return any results for URL {}'.format(url))
        return '', set()

    # Go through all terms found by the requested identifier and try to find the one where the _identifier_ and the
    # _term_ come from the same ontology (marked by a special flag). Example of such a situation would be a MONDO term
    # in the MONDO ontology. Example of a reverse situation is a MONDO term in EFO ontology (being *imported* into it
    # at some point).
    label = ''
    synonyms = set()
    for term in json_response['elements']:
        if term['isDefiningOntology']:
            if len(term['label']) > 1:
                logger.warning(f'Found multiple labels for {ontology_uri}, choosing the first')
            label = term['label'][0]
        # Synonyms are not always in the defining ontology, so we accumulate all exact synonyms from all terms
        # Also this value can be either a single string or a list of strings _and/or_ dicts (!)
        if EXACT_SYNONYM_KEY in term:
            if isinstance(term[EXACT_SYNONYM_KEY], str):
                synonyms.add(term[EXACT_SYNONYM_KEY])
            elif isinstance(term[EXACT_SYNONYM_KEY], list):
                synonym_values = get_as_string_list(term[EXACT_SYNONYM_KEY])
                synonyms.update(synonym_values)
    if label is None:
        if '/medgen/' not in url and '/omim/' not in url:
            logger.warning('OLS queried OK, but there is no defining ontology in its results for URL {}'.format(url))
    return label, synonyms


def get_as_string_list(field_value):
    """ Takes a list of strings and dicts as returned by OLS and return a list of strings only. """
    return [val.lower().strip() if isinstance(val, str)
            else val['value'].lower().strip() for val in field_value]


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
    response = requests.get(f"{OLS_BASE_URL}/ontologies/{ontology}/classes/{double_encoded_uri}")
    # V1 of the API returned 404 when a term was not present in the ontology, in which case we do not want to retry.
    # V2 returns 500 in this case, so to preserve this behaviour we check the error message as well.
    if 500 <= response.status_code < 600 and 'Expected at least 1 result' not in response.text:
        raise ServerError(f'Error for {uri}')
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
    return not response_json["isObsolete"]


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
    if REPLACEMENT_KEY in response_json and response_json[REPLACEMENT_KEY]:
        replacement_uri = response_json[REPLACEMENT_KEY]
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
    # V2 of the OLS API does not support search currently, so for now use V1
    search_url = f'https://www.ebi.ac.uk/ols4/api/search?ontology={ontology}&q={text}&queryFields=label&exact=true'
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


def get_fields_with_match(search_term, query_fields, result_json):
    search_term = search_term.lower().strip()
    search_term_tokens = set(search_term.split())
    full_exact_match = []
    contained_match = []
    token_match = []
    for field in query_fields:
        if field in result_json:
            if isinstance(result_json[field], str):
                field_value = result_json[field].lower().strip()
                if search_term == field_value:
                    full_exact_match.append(field)
                elif search_term in field_value:
                    contained_match.append(field)
                elif search_term_tokens.intersection(field_value.split()):
                    token_match.append(field)
            if isinstance(result_json[field], list):
                field_values = get_as_string_list(result_json[field])
                if [element for element in field_values if search_term == element]:
                    full_exact_match.append(field)
                elif [element for element in field_values if search_term in element]:
                    contained_match.append(field)
                elif [search_term_tokens.intersection(element.split()) for element in field_values]:
                    token_match.append(field)

    return full_exact_match, contained_match, token_match


def get_is_in_ontologies(uri, mapping_context):
    in_target_ontology = is_in_ontology(uri, mapping_context.target_ontology)
    in_preferred_ontology = False
    for ontology in mapping_context.preferred_ontologies:
        if is_in_ontology(uri, ontology):
            in_preferred_ontology = True
            break
    return in_target_ontology, in_preferred_ontology
