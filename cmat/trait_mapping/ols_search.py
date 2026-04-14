import logging
import requests

from cmat.trait_mapping.ols import ols_ontology_query, EXACT_SYNONYM_KEY, get_as_string_list
from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingProvenance
from cmat.trait_mapping.utils import json_request

logger = logging.getLogger(__package__)


class OlsMapping(OntologyMapping):
    def __init__(self, mapping_context, uri, label, in_target_ontology,
                 in_preferred_ontology, is_current, exact_match, contained_match, token_match):
        super().__init__(mapping_context, uri, MappingProvenance.OLS, label,
                         in_target_ontology, in_preferred_ontology, is_current, exact_match, contained_match,
                         token_match)


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


def get_ols_search_results(mapping_context, query_fields, field_list):
    """
    Search OLS for a given trait name with the specified parameters.

    :param trait_name: String containing a trait name from a ClinVar record.
    :param ontologies: String containing list of ontologies to search
    :param query_fields: String containing list of fields to query
    :param field_list: String containing list of fields to return
    :param target_ontology: ID of target ontology
    :param preferred_ontologies: List of preferred non-target ontology IDs
    :return: List of OlsResults
    """
    if query_fields is None or field_list is None:
        return []
    query_fields_list = query_fields.split(',')
    # V2 of the OLS API does not support search currently, so for now use V1
    search_url = 'https://www.ebi.ac.uk/ols4/api/search'
    params = {
        'q': mapping_context.trait_name,
        'exact': 'true',
        'obsoletes': 'false',
        'ontologies': f'{mapping_context.target_ontology.lower()},{",".join(mapping_context.preferred_ontologies)}',
        'queryFields': query_fields,
        'fieldList': field_list,
        'rows': 1000
    }

    try:
        results = json_request(search_url, params=params)
        if results['response']['numFound'] > 0:
            search_results = set()

            for result in results['response']['docs']:
                uri = result.get('iri')
                label = result.get('label')
                ontology = result.get('ontology_name')
                full_exact_match, contained_match, token_match = get_fields_with_match(mapping_context.trait_name, query_fields_list, result)
                in_target_ontology = (ontology == mapping_context.target_ontology.lower())
                in_preferred_ontology = (ontology in mapping_context.preferred_ontologies)
                # Query includes obsoletes=false
                is_current = True if in_target_ontology else False
                # If one of the matched fields is synonym, we must make an additional V2 API query in order to check
                # that the synonym is exact, as the V1 search results do not separate synonym types.
                if any('synonym' in l for l in [full_exact_match, contained_match, token_match]):
                    classes_response = ols_ontology_query(uri, ontology)
                    if classes_response.status_code != 200:
                        continue
                    full_exact_match, contained_match, token_match = get_fields_with_match(
                        mapping_context.trait_name,
                        [f if f != 'synonym' else EXACT_SYNONYM_KEY  for f in query_fields_list],
                        classes_response.json()
                    )
                # Need to do this check, in case the only matches were to non-exact synonyms
                if full_exact_match or contained_match or token_match:
                    search_results.add(OlsMapping(mapping_context, uri, label, in_target_ontology, in_preferred_ontology, is_current,
                                                  full_exact_match, contained_match, token_match))
            return list(search_results)
        else:
            return []

    except requests.RequestException as e:
        logger.warning(f"Error querying OLS4: {e}")
        return []
