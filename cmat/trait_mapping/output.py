import csv
import logging
from collections import Counter

from cmat.trait_mapping import ols
from cmat.trait_mapping.ols import MappingSource, MatchType, OlsResult
from cmat.trait_mapping.trait import Trait

logger = logging.getLogger(__package__)


def output_trait_mapping(trait: Trait, mapping_writer: csv.writer, finished_source_counts: Counter = None):
    """
    Write any finished ontology mappings for a trait to a csv file writer.

    :param trait: A trait with finished ontology mappings in finished_mapping_set
    :param mapping_writer: A csv.writer to write the finished mappings
    :param finished_source_counts: Optional Counter to count sources of finished mappings
    """
    for ontology_entry in trait.finished_mapping_set:
        # Need the corresponding Zooma result - for counting purposes only
        zooma_mapping = None
        for zooma_result in trait.zooma_result_list:
            for zm in zooma_result.mapping_list:
                if (zm.in_ontology and zm.is_current and ontology_entry.uri == zm.uri
                        and ontology_entry.label == zm.ontology_label):
                    zooma_mapping = zm
                    break
        if zooma_mapping and finished_source_counts:
            finished_source_counts[zooma_mapping.source.lower()] += 1
        mapping_writer.writerow([trait.name, ontology_entry.uri, ontology_entry.label])


def to_mapping_string(uri, trait_name, target_ontology, preferred_ontologies):
    label, match_type, mapping_source = get_mapping_attributes_from_ols(trait_name, uri, target_ontology, preferred_ontologies)
    return '|'.join([uri, label, str(match_type), mapping_source.to_string(target_ontology, preferred_ontologies)])


def get_zooma_mappings(result_list, trait_name, target_ontology, preferred_ontologies):
    """
    Two types of ZOOMA mappings are extracted as candidates for curation:
     1. High confidence mappings (previously accepted as finished automated mappings)
     2. Exact label matches (outside of target or preferred ontologies, as these are covered by OLS)
    """
    high_conf_mappings = []
    exact_mappings = []
    for result in result_list:
        for mapping in result.mapping_list:
            if mapping.in_ontology and mapping.is_current and result.confidence.lower() == 'high':
                high_conf_mappings.append(to_mapping_string(mapping.uri, trait_name, target_ontology, preferred_ontologies))
            elif mapping.exact_match:
                exact_mappings.append(to_mapping_string(mapping.uri, trait_name, target_ontology, preferred_ontologies))
    return high_conf_mappings, exact_mappings


def get_oxo_mappings(result_list, trait_name, target_ontology, preferred_ontologies):
    """
    Two types of OxO mappings are candidates for curation:
     1. Distance-1 mappings (previously accepted as finished automated mappings)
     2. Exact label matches (outside of target or preferred ontologies, as these are covered by OLS)
    """
    dist_one_mappings = []
    exact_mappings = []
    for result in result_list:
        for mapping in result.mapping_list:
            if mapping.in_ontology and mapping.is_current and mapping.distance == 1:
                dist_one_mappings.append(to_mapping_string(mapping.uri.uri, trait_name, target_ontology, preferred_ontologies))
            elif mapping.exact_match:
                exact_mappings.append(to_mapping_string(mapping.uri.uri, trait_name, target_ontology, preferred_ontologies))
    return dist_one_mappings, exact_mappings


def get_previous_and_replacement_mappings(previous_mappings, trait_name, target_ontology, preferred_ontologies):
    previous_and_replacement = []
    for uri, label in previous_mappings:
        label, match_type, mapping_source = get_mapping_attributes_from_ols(trait_name, uri, target_ontology, preferred_ontologies)
        trait_string = '|'.join([uri, label, str(match_type), mapping_source.to_string(target_ontology, preferred_ontologies)])
        replacement_string = ''
        if mapping_source == MappingSource.TARGET_OBSOLETE:
            replacement_string = find_replacement_mapping(trait_name, uri, target_ontology, preferred_ontologies)
        previous_and_replacement.append((trait_string, replacement_string))
    return previous_and_replacement


def find_replacement_mapping(trait_name, previous_uri, ontology, preferred_ontologies, max_depth=1):
    replacement_uri = ols.get_replacement_term(previous_uri, ontology)
    if not replacement_uri:
        return ''
    label, match_type, mapping_source = get_mapping_attributes_from_ols(trait_name, replacement_uri, ontology,
                                                                        preferred_ontologies)
    # If this term is also obsolete, try to find its replacement (at most max_depth times)
    if mapping_source == MappingSource.TARGET_OBSOLETE and replacement_uri.startswith('http') and max_depth > 0:
        return find_replacement_mapping(trait_name, replacement_uri, ontology, preferred_ontologies,
                                        max_depth=max_depth-1)
    trait_string = '|'.join([replacement_uri, label, str(match_type),
                             mapping_source.to_string(ontology, preferred_ontologies)])
    return trait_string


def find_exact_mappings(ols_results, target_ontology, preferred_ontologies):
    """Returns the top ranked exact label match and exact synonym match mappings, along with the remaining mappings."""
    exact_label_match_str = ''
    exact_synonym_match_str = ''
    other_mapping_strs = []
    for result in ols_results:
        match_type = result.get_match_type()
        mapping_source = result.get_mapping_source()
        mapping_str = '|'.join([result.uri, result.label, str(match_type),
                                mapping_source.to_string(target_ontology, preferred_ontologies)])
        if match_type == MatchType.EXACT_MATCH_LABEL and exact_label_match_str == '':
            exact_label_match_str = mapping_str
        elif match_type == MatchType.EXACT_MATCH_SYNONYM and exact_synonym_match_str == '':
            exact_synonym_match_str = mapping_str
        else:
            other_mapping_strs.append(mapping_str)
    return exact_label_match_str, exact_synonym_match_str, other_mapping_strs


def get_mapping_attributes_from_ols(trait_name, uri, target_ontology, preferred_ontologies):
    try:
        in_target_ontology, in_preferred_ontology = ols.get_is_in_ontologies(uri, target_ontology, preferred_ontologies)
        is_current = ols.is_current_and_in_ontology(uri, target_ontology) if in_target_ontology else False

        label, synonyms = ols.get_label_and_synonyms_from_ols(uri)
        exact_match, contained_match, token_match = ols.get_fields_with_match(
            trait_name, ['label', ols.EXACT_SYNONYM_KEY], {'label': label, ols.EXACT_SYNONYM_KEY: list(synonyms)})

        ols_result = OlsResult(uri, label, None, exact_match, contained_match, token_match, in_target_ontology,
                               in_preferred_ontology, is_current)
        return label, ols_result.get_match_type(), ols_result.get_mapping_source()
    except Exception as e:
        logger.warning(f'Error while getting mapping attributes from OLS: {e}')
        return '', '', ''


def get_exact_match_str(exact_match_ols, exact_match_zooma, exact_match_oxo):
    if exact_match_ols:
        return exact_match_ols
    # TODO check the ordering of these
    if exact_match_zooma:
        return exact_match_zooma[0]
    if exact_match_oxo:
        return exact_match_oxo[0]
    return ''


def output_for_curation(trait: Trait, curation_writer: csv.writer, target_ontology: str, preferred_ontologies: list):
    """
    Write any non-finished OLS, Zooma or OxO mappings of a trait to a file for manual curation.
    Also outputs traits without any ontology mappings.

    :param trait: A Trait with no finished ontology mappings in finished_mapping_set
    :param target_ontology: ID of target ontology
    :param preferred_ontologies: List of preferred non-target ontology IDs
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    """
    # Traits which are associated with NT expansion variants should be prioritised and curated even if the number of
    # records they are associated with is low. This is added to the "Notes" column.
    output_row = [trait.name, trait.frequency, 'NT expansion' if trait.associated_with_nt_expansion else '']

    # TODO consider moving the candidate processing outside the "output" section
    # Collect candidate mappings to use
    previous_and_replacement = get_previous_and_replacement_mappings(trait.previous_mapping_list, trait.name,
                                                                     target_ontology, preferred_ontologies)
    exact_match_ols_str, exact_synonym_match_str, other_ols_mapping_strs = find_exact_mappings(trait.ols_result_list,
                                                                                               target_ontology,
                                                                                               preferred_ontologies)
    high_zooma_conf_strs, exact_match_zooma_strs = get_zooma_mappings(trait.zooma_result_list, trait.name,
                                                                      target_ontology, preferred_ontologies)
    oxo_dist_one_strs, exact_match_oxo_strs = get_oxo_mappings(trait.oxo_result_list, trait.name,
                                                               target_ontology, preferred_ontologies)
    exact_match_str = get_exact_match_str(exact_match_ols_str, exact_match_zooma_strs, exact_match_oxo_strs)

    # Output result
    for previous_str, replacement_str in previous_and_replacement:
        for zooma_str in high_zooma_conf_strs:
            for oxo_str in oxo_dist_one_strs:
                curation_writer.writerow(
                    output_row
                    # Dedicated columns
                    + [previous_str, replacement_str, exact_match_str, exact_synonym_match_str, zooma_str, oxo_str]
                    # Other mappings, limited to at most 50
                    + other_ols_mapping_strs[:50]
                )


def output_trait(trait: Trait, mapping_writer: csv.writer, curation_writer: csv.writer, finished_source_counts: Counter,
                 target_ontology: str, preferred_ontologies: list):
    """
    Output finished ontology mappings of a trait, or non-finished mappings (if any) for curation.

    :param trait: A trait which has been used to query Zooma and possibly OxO.
    :param mapping_writer: A csv.writer to write the finished mappings
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    :param target_ontology: ID of target ontology
    :param preferred_ontologies: List of preferred non-target ontology IDs
    """
    if trait.is_finished:
        output_trait_mapping(trait, mapping_writer, finished_source_counts)
    else:
        output_for_curation(trait, curation_writer, target_ontology, preferred_ontologies)
