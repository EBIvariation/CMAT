import os
import re
from functools import lru_cache
import logging
import requests
import urllib

from retry import retry

from cmat.trait_mapping.ontology_uri import OntologyUri
from cmat.trait_mapping.utils import json_request, ServerError

OLS_SERVER = 'https://www.ebi.ac.uk/ols4'
# The setting for local OLS installation should be uncommented if necessary. Note that the link
# for the local deployment is different from the production link in three regards: (1) it must use
# HTTP instead of HTTPS; (2) it must include the port which you used when deploying the Docker
# container; (3) it does *not* include /ols in its path.
# OLS_EFO_SERVER = 'http://127.0.0.1:8080'

logger = logging.getLogger(__package__)


def build_ols_query(ontology_uri: str) -> str:
    """Build a url to query OLS for a given ontology uri."""
    return "{}/api/terms?iri={}".format(OLS_SERVER, ontology_uri)


@lru_cache(maxsize=16384)
def get_ontology_label_from_ols(ontology_uri: str) -> str:
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
            return term["label"]

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
    response = requests.get(f"{OLS_SERVER}/api/ontologies/{ontology}/terms/{double_encoded_uri}")
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
    search_url = os.path.join(OLS_SERVER, f'api/search?ontology={ontology}&q={text}&queryFields=label&exact=true')
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
