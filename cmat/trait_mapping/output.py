import csv
import logging
from collections import Counter

from cmat.clinvar_xml_io.ontology_uri import OntologyUri
from cmat.trait_mapping.ols import get_replacement_term
from cmat.trait_mapping.ontology_mapping import MappingProvenance, MappingSource, MatchType, OntologyMapping, \
    PreviousMapping, MappingContext, sort_and_deduplicate_mappings
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
        if finished_source_counts:
            # Get the corresponding provenance for counting purposes
            for mapping in trait.candidate_mappings:
                if ontology_entry.uri == mapping.uri:
                    finished_source_counts[mapping.provenance] += 1
                    break
        mapping_writer.writerow([trait.name, ontology_entry.uri, ontology_entry.label])


def get_previous_and_replacement_mappings(candidate_mappings, trait_name, target_ontology, preferred_ontologies):
    previous_and_replacement = []
    remaining_mappings = []
    for mapping in candidate_mappings:
        if mapping.provenance == MappingProvenance.PREVIOUS:
            trait_string = str(mapping)
            replacement_string = ''
            if mapping.get_mapping_source() == MappingSource.TARGET_OBSOLETE:
                replacement_string = find_replacement_mapping(trait_name, mapping.uri, target_ontology, preferred_ontologies)
            previous_and_replacement.append((trait_string, replacement_string))
        else:
            remaining_mappings.append(mapping)
    if not previous_and_replacement:
        return [('', '')], candidate_mappings
    return previous_and_replacement, remaining_mappings


def find_replacement_mapping(trait_name, previous_uri, ontology, preferred_ontologies, max_depth=1):
    replacement_uri = get_replacement_term(previous_uri, ontology)
    if not replacement_uri or not replacement_uri.startswith('http'):
        return ''
    replacement_mapping = OntologyMapping(MappingContext(trait_name, ontology, preferred_ontologies),
                                          replacement_uri, MappingProvenance.PREVIOUS)
    # If this term is also obsolete, try to find its replacement (at most max_depth times)
    if replacement_mapping.get_mapping_source() == MappingSource.TARGET_OBSOLETE and max_depth > 0:
        return find_replacement_mapping(trait_name, replacement_uri, ontology, preferred_ontologies,
                                        max_depth=max_depth-1)
    return str(replacement_mapping)


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

    # Pull out previous and replacement mappings
    previous_and_replacement, remaining_mappings = get_previous_and_replacement_mappings(
        trait.candidate_mappings, trait.name, target_ontology, preferred_ontologies)
    # From the rest, pull out top-ranked exact label and exact synonym matches
    sorted_candidates = sort_and_deduplicate_mappings(remaining_mappings)
    exact_match_str = ''
    exact_synonym_match_str = ''
    other_mapping_strs = []
    for mapping in sorted_candidates:
        if exact_match_str == '' and mapping.get_match_type() == MatchType.EXACT_MATCH_LABEL:
            exact_match_str = str(mapping)
        elif exact_synonym_match_str == '' and mapping.get_match_type() == MatchType.EXACT_MATCH_SYNONYM:
            exact_synonym_match_str = str(mapping)
        else:
            other_mapping_strs.append(str(mapping))

    for previous_str, replacement_str in previous_and_replacement:
            curation_writer.writerow(
                output_row
                # Dedicated columns
                + [previous_str, replacement_str, exact_match_str, exact_synonym_match_str]
                # Other mappings, limited to at most 50
                + other_mapping_strs[:50]
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
