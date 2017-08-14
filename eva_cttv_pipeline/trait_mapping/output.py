import csv

from eva_cttv_pipeline.trait_mapping.trait import Trait


def output_trait_mapping(trait: Trait, mapping_writer: csv.writer):
    """
    Write any finished ontology mappings for a trait to a csv file writer.

    :param trait: A trait with finished ontology mappings in finished_mapping_set
    :param mapping_writer: A csv.writer to write the finished mappings
    """
    for ontology_entry in trait.finished_mapping_set:
        mapping_writer.writerow([trait.name, ontology_entry.uri, ontology_entry.label])


def get_zooma_mappings_for_curation(trait: Trait) -> list:
    zooma_entry_list = []
    for zooma_mapping in trait.zooma_mapping_list:
        for zooma_entry in zooma_mapping.zooma_entry_list:
            if zooma_entry.in_efo and zooma_entry.is_current:
                zooma_entry_list.append(zooma_entry)
    zooma_entry_list.sort(reverse=True)
    return zooma_entry_list


# TODO best way to unite this and the above very similar method?
def get_oxo_mappings_for_curation(trait: Trait) -> list:
    oxo_mapping_list = []
    for oxo_result in trait.oxo_xref_list:
        for oxo_mapping in oxo_result.oxo_mapping_list:
            if oxo_mapping.in_efo and oxo_mapping.is_current:
                oxo_mapping_list.append(oxo_mapping)
    oxo_mapping_list.sort(reverse=True)
    return oxo_mapping_list


def output_for_curation(trait: Trait, curation_writer: csv.writer):
    """
    Write any non-finished Zooma or OxO mappings of a trait to a file for manual curation.
    Also outputs traits without any ontology mappings.

    :param trait: A Trait with no finished ontology mappings in finished_mapping_set
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    """
    output_row = []
    output_row.extend([trait.name, trait.frequency])

    zooma_entry_list = get_zooma_mappings_for_curation(trait)

    for zooma_entry in zooma_entry_list:
        cell = [zooma_entry.uri, zooma_entry.ontology_label, str(zooma_entry.confidence),
                zooma_entry.source]
        output_row.append("|".join(cell))

    oxo_mapping_list = get_oxo_mappings_for_curation(trait)

    for oxo_mapping in oxo_mapping_list:
        cell = [str(oxo_mapping.uri), oxo_mapping.ontology_label, str(oxo_mapping.distance),
                oxo_mapping.query_id]
        output_row.append("|".join(cell))

    curation_writer.writerow(output_row)


def output_trait(trait: Trait, mapping_writer: csv.writer, curation_writer: csv.writer):
    """
    Output either any finished ontology mappings of a trait, or any non-finished mappings, if any.

    :param trait: A trait which has been used to query Zooma and possibly OxO.
    :param mapping_writer: A csv.writer to write the finished mappings
    :param curation_writer: A csv.writer to write non-finished ontology mappings for manual curation
    """
    if trait.is_finished:
        output_trait_mapping(trait, mapping_writer)
    else:
        output_for_curation(trait, curation_writer)