import csv
from collections import Counter

from cmat.trait_mapping.trait import Trait


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


def get_mappings_for_curation(result_list) -> list:
    """Sorted in reverse so the highest ranked oxo mappings are shown first"""
    curation_mapping_list = []
    for result in result_list:
        for mapping in result.mapping_list:
            if (mapping.in_ontology and mapping.is_current) or (not mapping.in_ontology):
                curation_mapping_list.append(mapping)
    curation_mapping_list.sort(reverse=True)
    return curation_mapping_list


def output_for_curation(trait: Trait, curation_writer: csv.writer, target_ontology: str, preferred_ontologies: list):
    """
    Write any non-finished OLS mappings of a trait to a file for manual curation.
    Also outputs traits without any ontology mappings.

    :param trait: A Trait with no finished ontology mappings in finished_mapping_set
    :param target_ontology: ID of target ontology
    :param preferred_ontologies: List of preferred non-target ontology IDs
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    """

    # Traits which are associated with NT expansion variants should be prioritised and curated even if the number of
    # records they are associated with is low. This is added to the "Notes" column.
    output_row = [trait.name, trait.frequency, 'NT expansion' if trait.associated_with_nt_expansion else '']

    for ols_result in sorted(trait.ols_result_list, reverse=True):
        match_type = ols_result.get_match_type()
        mapping_source = ols_result.get_mapping_source()
        cell = [ols_result.uri, ols_result.label, str(match_type), mapping_source.to_string(target_ontology, preferred_ontologies)]
        output_row.append("|".join(cell))

    curation_writer.writerow(output_row)


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
