import logging
from functools import lru_cache

from requests import RequestException

from cmat.clinvar_xml_io.ontology_uri import OntologyUri
from cmat.trait_mapping.utils import json_request
from cmat.trait_mapping.ols import build_ols_query, EXACT_SYNONYM_KEY, get_as_string_list, OLS_BASE_URL, \
    double_encode_uri, REPLACEMENT_KEY

logger = logging.getLogger(__package__)

EXACT_MATCH_KEY = 'http://www.w3.org/2004/02/skos/core#exactMatch'


@lru_cache
def fetch_eval_data(*, db_iden=None, uri=None, include_neighbors=False, target_ontology='EFO'):
    """
    Query OLS for this ontology identifier and extract the following:
    - Whether the term is obsolete in target ontology (default EFO)
    - Synonyms (replacement terms or exact matches)
    - Parents and children in target ontology
    """
    if db_iden:
        db, iden = db_iden
        ontology_uri = OntologyUri(iden, db).uri
    elif uri:
        ontology_uri = uri
    else:
        logger.warning("Must provide either DB + identifier or full URI")
        return None
    curie = OntologyUri.uri_to_curie(ontology_uri)

    # Defaults to return if OLS query fails or no term in target ontology
    is_obsolete = False
    synonyms = {}
    parents = {}
    children = {}

    url = build_ols_query(ontology_uri, include_obsoletes=True)
    try:
        json_response = json_request(url)
    except RequestException:
        logger.warning(f'OLS4 error for {url}, trying OLS3...')
        json_response = json_request(url.replace('/ols4/api/v2/', '/ols/api'))
    if json_response and 'elements' in json_response:
        for term in json_response['elements']:
            # Get only target ontology terms (even if imported)
            if term['ontologyId'].lower() == target_ontology.lower():
                synonyms, is_obsolete = extract_synonyms_and_obsolete(term)
                # If requested, fetch the parents and children of this term
                if include_neighbors:
                    parents, children = extract_parents_and_children(term)

    if include_neighbors:
        return curie, is_obsolete, synonyms, parents, children
    return curie, is_obsolete, synonyms


def extract_synonyms_and_obsolete(ontology_term):
    synonyms = {ontology_term['iri']}
    is_obsolete = ontology_term['isObsolete']

    # Add replacement term if this one is obsolete
    if is_obsolete and ontology_term[REPLACEMENT_KEY]:
        synonyms.add(ontology_term[REPLACEMENT_KEY])
    # Also add exact matches
    if EXACT_MATCH_KEY in ontology_term:
        synonyms.update(get_as_string_list(ontology_term[EXACT_MATCH_KEY]))
    if EXACT_SYNONYM_KEY in ontology_term:
        synonyms.update(get_as_string_list(ontology_term[EXACT_SYNONYM_KEY]))

    # Synonyms contains current included URIs, convert to DB:ID style
    synonyms = {OntologyUri.uri_to_curie(s) for s in synonyms}
    # Filter out Nones
    synonyms = {s for s in synonyms if s is not None}
    return synonyms, is_obsolete


def extract_parents_and_children(ontology_term):
    parents = {OntologyUri.uri_to_curie(p) for p in get_as_string_list(ontology_term.get('directParent', []))}
    # V2 of OLS API does not include children directly in the response, need to hit a separate endpoint
    children = get_children_curies(ontology_term['iri'], ontology_term['definedBy'][0])
    return parents, children


def get_children_curies(uri, ontology):
    curies = set()
    children_endpoint = f'{OLS_BASE_URL}/ontologies/{ontology}/classes/{double_encode_uri(uri)}/children'
    json_response = json_request(children_endpoint)
    if json_response and 'elements' in json_response:
        for term in json_response['elements']:
            curies.add(term['curie'])
    return curies
