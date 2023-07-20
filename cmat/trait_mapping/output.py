import csv
from collections import Counter

from cmat.trait_mapping.trait import Trait


def output_trait_mapping(trait: Trait, mapping_writer: csv.writer, finished_source_counts: Counter):
    """
    Write any finished ontology mappings for a trait to a csv file writer.

    :param trait: A trait with finished ontology mappings in finished_mapping_set
    :param mapping_writer: A csv.writer to write the finished mappings
    """
    for ontology_entry in trait.finished_mapping_set:
        # Need the corresponding Zooma result
        zooma_mapping = None
        for zm in trait.zooma_result_list:
            if ontology_entry.uri == zm.uri and ontology_entry.label == zm.ontology_label:
                zooma_mapping = zm
        if zooma_mapping:
            finished_source_counts[zooma_mapping.source.lower()] += 1
        mapping_writer.writerow([trait.name, ontology_entry.uri, ontology_entry.label])


def get_mappings_for_curation(result_list) -> list:
    """Sorted in reverse so the highest ranked oxo mappings are shown first"""
    curation_mapping_list = []
    for result in result_list:
        for mapping in result.mapping_list:
            if (mapping.in_efo and mapping.is_current) or (not mapping.in_efo):
                curation_mapping_list.append(mapping)
    curation_mapping_list.sort(reverse=True)
    return curation_mapping_list


def output_for_curation(trait: Trait, curation_writer: csv.writer):
    """
    Write any non-finished Zooma or OxO mappings of a trait to a file for manual curation.
    Also outputs traits without any ontology mappings.

    :param trait: A Trait with no finished ontology mappings in finished_mapping_set
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    """

    # Traits which are associated with NT expansion variants should be prioritised and curated even if the number of
    # records they are associated with is low. This is added to the "Notes" column.
    output_row = [trait.name, trait.frequency, 'NT expansion' if trait.associated_with_nt_expansion else '']

    zooma_mapping_list = get_mappings_for_curation(trait.zooma_result_list)

    for zooma_mapping in zooma_mapping_list:
        cell = [zooma_mapping.uri, zooma_mapping.ontology_label, str(zooma_mapping.confidence),
                zooma_mapping.source, 'EFO_CURRENT' if zooma_mapping.in_efo else 'NOT_CONTAINED']
        output_row.append("|".join(cell))

    oxo_mapping_list = get_mappings_for_curation(trait.oxo_result_list)

    for oxo_mapping in oxo_mapping_list:
        cell = [str(oxo_mapping.uri), oxo_mapping.ontology_label, str(oxo_mapping.distance),
                oxo_mapping.query_id, 'EFO_CURRENT' if oxo_mapping.in_efo else 'NOT_CONTAINED']
        output_row.append("|".join(cell))

    curation_writer.writerow(output_row)


def output_trait(trait: Trait, mapping_writer: csv.writer, curation_writer: csv.writer, finished_source_counts: Counter):
    """
    Output finished ontology mappings of a trait, or non-finished mappings (if any) for curation.

    :param trait: A trait which has been used to query Zooma and possibly OxO.
    :param mapping_writer: A csv.writer to write the finished mappings
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    """
    if trait.is_finished:
        output_trait_mapping(trait, mapping_writer, finished_source_counts)
    else:
        output_for_curation(trait, curation_writer)
