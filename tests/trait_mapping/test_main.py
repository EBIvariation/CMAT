"""Tests for the trait mapping pipeline. Test resources are compressed XML files which contain one or a few records
manually extracted from the main ClinVar XML to check specific cases."""
import csv
import os
import tempfile

import pytest

from cmat.trait_mapping.main import parse_traits, process_traits, process_trait
from cmat.trait_mapping.trait import Trait


def get_test_resource(resource_name):
    """Gets full path to the test resource located in the same directory as the test module."""

    # Full path to this module.
    this_module = os.path.abspath(__file__)

    # Full path to the directory where it is contained.
    module_directory = os.path.dirname(this_module)

    # Full path to the requested resource.
    return os.path.join(module_directory, 'resources', resource_name)


def run_pipeline(resource_name):
    """Runs the pipeline on a given test resource and returns the output traits, automated mappings, and curation terms
    as lists of lists."""
    input_filename = get_test_resource(resource_name)
    traits_file, mappings_file, curation_file = [tempfile.NamedTemporaryFile(delete=False) for _ in range(3)]
    filters = {
        'ontologies': 'efo,ordo,hp,mondo',
        'required': 'cttv,eva-clinvar,clinvar-xrefs,gwas',
        'preferred': 'eva-clinvar,cttv,gwas,clinvar-xrefs',
    }
    parse_traits(
        input_filepath=input_filename,
        output_traits_filepath=traits_file.name,
    )
    process_traits(
        traits_filepath=traits_file.name,
        output_mappings_filepath=mappings_file.name,
        output_curation_filepath=curation_file.name,
        filters=filters,
        zooma_host='https://www.ebi.ac.uk',
        oxo_target_list=['Orphanet', 'efo', 'hp', 'mondo'],
        oxo_distance=3,
        ols_ontology_list='efo,hp,mondo',
        ols_query_fields='label,synonym',
        ols_field_list='iri,label,ontology_name,synonym',
        ontology='EFO'
    )
    output_traits = [row for row in csv.reader(open(traits_file.name), delimiter=',')]
    output_mappings = [line.rstrip().split('\t') for line in open(mappings_file.name).read().splitlines()]
    output_curation = [line.rstrip().split('\t') for line in open(curation_file.name).read().splitlines()]
    for temp_file in (traits_file, mappings_file, curation_file):
        os.remove(temp_file.name)
    return output_traits, output_mappings, output_curation


@pytest.mark.integration
def test_main():
    """Basic sanity test of output files, using a random sample of records."""
    output_traits, output_mappings, output_curation = run_pipeline('sample.xml.gz')
    all_terms = {x[0] for x in output_traits}
    mapped_terms = {x[0] for x in output_mappings}
    curation_terms = {x[0] for x in output_curation}
    assert len(mapped_terms) + len(curation_terms) == len(all_terms)


def test_process_trait_exact_match():
    # Exact match with MONDO:0009061 (in EFO and Mondo)
    trait_name = 'Cystic Fibrosis'
    # Use our default Zooma filters
    zooma_filters = {'ontologies': 'efo,ordo,hp,mondo',
                     'required': 'cttv,eva-clinvar,clinvar-xrefs,gwas',
                     'preferred': 'eva-clinvar,cttv,gwas,clinvar-xrefs'}
    zooma_host = 'https://www.ebi.ac.uk'
    # Don't use OxO
    oxo_targets = []
    oxo_distance = 0
    # Don't use OLS
    ols_ontology_list = None
    ols_query_fields = None
    ols_field_list = None

    # This should be marked as finished, as it's an exact string match with a term contained in the target ontology
    efo_trait = process_trait(Trait(trait_name, None, None), zooma_filters, zooma_host, oxo_targets, oxo_distance,
                              ols_ontology_list, ols_query_fields, ols_field_list, target_ontology='efo')
    assert efo_trait.is_finished

    # This should not be marked as finished, even though Zooma finds an exact match in one of its ontologies, it's not
    # the requested target ontology and thus still needs to be curated
    hpo_trait = process_trait(Trait(trait_name, None, None), zooma_filters, zooma_host, oxo_targets, oxo_distance,
                              ols_ontology_list, ols_query_fields, ols_field_list, target_ontology='hp')
    assert not hpo_trait.is_finished
