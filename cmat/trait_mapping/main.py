import csv
import logging
import multiprocessing
from collections import Counter

from cmat.clinvar_xml_io import ClinVarTrait
from cmat.trait_mapping.ols import get_ols_results
from cmat.trait_mapping.output import output_trait
from cmat.trait_mapping.oxo import get_oxo_results
from cmat.trait_mapping.oxo import uris_to_oxo_format
from cmat.trait_mapping.trait import Trait
from cmat.trait_mapping.trait_names_parsing import parse_trait_names
from cmat.trait_mapping.zooma import get_zooma_results

logger = logging.getLogger(__package__)


def get_uris_for_oxo(zooma_result_list: list) -> set:
    """
    For a list of Zooma mappings return a list of uris for the mappings in that list with a high
    confidence.

    :param zooma_result_list: List with elements of class ZoomaResult
    :return: set of uris from high confidence Zooma mappings, for which to query OxO
    """
    uri_set = set()
    for mapping in zooma_result_list:
        # Only use high confidence Zooma mappings for querying OxO
        if mapping.confidence.lower() == "high":
            uri_set.update([entry.uri for entry in mapping.mapping_list])
    return uri_set


def process_trait(trait: Trait, filters: dict, zooma_host: str, oxo_target_list: list, oxo_distance: int,
                  ols_ontology_list: str, ols_query_fields: str, ols_field_list: str,
                  target_ontology: str = 'EFO') -> Trait:
    """
    Process a single trait. First look for an exact string match in the target ontology and return immediately if found.
    Otherwise find any mappings in Zooma. If there are no high confidence Zooma mappings that are in EFO then query OxO
    with any high confidence mappings not in EFO.

    :param trait: The trait to be processed.
    :param filters: A dictionary of filters to use for querying Zooma.
    :param zooma_host: A string with the hostname to use for querying Zooma
    :param oxo_target_list: A list of strings, each being an OxO ID for an ontology. Used to specify
                            which ontologies should be queried using OxO.
    :param oxo_distance: int specifying the maximum number of steps to use to query OxO. i.e. OxO's
                         "distance" parameter.
    :param ols_ontology_list: A string listing ontologies used to query OLS
    :param ols_query_fields: A string listing query fields used to query OLS
    :param ols_field_list: A string listing fields to return from OLS query
    :param target_ontology: ID of target ontology (default EFO)
    :return: The original trait after querying Zooma and possibly OxO, with any results found.
    """
    logger.debug('Processing trait {}'.format(trait.name))

    trait.ols_result_list = get_ols_results(trait.name.lower(), ols_ontology_list, ols_query_fields, ols_field_list,
                                            target_ontology)
    trait.process_ols_results()
    if trait.is_finished:
        return trait

    trait.zooma_result_list = get_zooma_results(trait.name.lower(), filters, zooma_host, target_ontology)
    trait.process_zooma_results()
    if (trait.is_finished
            or len(trait.zooma_result_list) == 0
            or any([entry.is_current
                    for mapping in trait.zooma_result_list
                    for entry in mapping.mapping_list])):
        return trait

    uris_for_oxo_set = get_uris_for_oxo(trait.zooma_result_list)
    oxo_input_id_list = uris_to_oxo_format(uris_for_oxo_set)
    if len(oxo_input_id_list) == 0:
        return trait
    trait.oxo_result_list = get_oxo_results(oxo_input_id_list, oxo_target_list, oxo_distance)
    if not trait.oxo_result_list:
        logger.debug('No OxO mapping for trait {}'.format(trait.name))
    trait.process_oxo_mappings()

    return trait


def output_traits_to_csv(trait_list, output_filepath, for_platform=False):
    """Output traits as a CSV file, formatted for curation platform integration if required."""
    with open(output_filepath, 'w') as output_file:
        writer = csv.writer(output_file, delimiter=',')
        if for_platform:
            writer.writerow(['text', 'upstreamId', 'priority'])
        for trait in trait_list:
            row = [trait.name, trait.identifier, trait.frequency]
            if not for_platform:
                row.append(trait.associated_with_nt_expansion)
            writer.writerow(row)


def read_traits_from_csv(traits_filepath):
    traits = []
    with open(traits_filepath, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=',')
        for row in reader:
            traits.append(Trait(row[0], row[1], int(row[2]), row[3] == 'True'))
    return traits


def parse_traits(input_filepath, output_traits_filepath, output_for_platform=None):
    logger.info('Started parsing trait names')
    trait_list = parse_trait_names(input_filepath)
    logger.info("Loaded {} trait names".format(len(trait_list)))
    # Remove non-specific trait names which should never be output
    trait_list = [trait for trait in trait_list if trait.name.lower() not in ClinVarTrait.NONSPECIFIC_TRAITS]
    output_traits_to_csv(trait_list, output_traits_filepath)
    logger.info("Output {} valid trait names".format(len(trait_list)))
    # Output an extra csv file for curation platform if path is provided
    if output_for_platform:
        output_traits_to_csv(trait_list, output_for_platform, True)


def process_traits(traits_filepath, output_mappings_filepath, output_curation_filepath, filters, zooma_host,
                   oxo_target_list, oxo_distance, ols_ontology_list, ols_query_fields, ols_field_list, ontology):
    trait_list = read_traits_from_csv(traits_filepath)
    logger.info(f'Read {len(trait_list)} traits from file')
    with open(output_mappings_filepath, "w", newline='') as mapping_file, \
            open(output_curation_filepath, "wt") as curation_file:
        mapping_writer = csv.writer(mapping_file, delimiter="\t")
        curation_writer = csv.writer(curation_file, delimiter="\t")

        logger.info('Processing trait names in parallel')
        trait_process_pool = multiprocessing.Pool(processes=24)
        processed_trait_list = [
            trait_process_pool.apply(
                process_trait,
                args=(trait, filters, zooma_host, oxo_target_list, oxo_distance, ols_ontology_list, ols_query_fields,
                      ols_field_list, ontology)
            )
            for trait in trait_list
        ]

        logger.info('Writing output with the processed traits')
        finished_source_counts = Counter()
        for trait in processed_trait_list:
            output_trait(trait, mapping_writer, curation_writer, finished_source_counts, ontology)

    logger.info('Finished processing trait names')
    logger.info(f'Source counts for finished mappings: {finished_source_counts}')
