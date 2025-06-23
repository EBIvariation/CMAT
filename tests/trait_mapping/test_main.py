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
        ols_query_fields='label,synonym',
        ols_field_list='iri,label,ontology_name,synonym',
        target_ontology='EFO',
        preferred_ontologies=['hp', 'mondo']
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


@pytest.mark.integration
def test_process_trait():
    # Use all default filters
    zooma_filters = {'ontologies': 'efo,ordo,hp,mondo',
                     'required': 'cttv,eva-clinvar,clinvar-xrefs,gwas',
                     'preferred': 'eva-clinvar,cttv,gwas,clinvar-xrefs'}
    zooma_host = 'https://www.ebi.ac.uk'
    oxo_targets = ['Orphanet', 'efo', 'hp', 'mondo']
    oxo_distance = 3
    ols_query_fields = 'label,synonym'
    ols_field_list = 'iri,label,ontology_name,synonym'
    target_ontology = 'EFO'
    preferred_ontologies = 'mondo,hp'

    # Trait 1 only goes through OLS as it finds an exact match in EFO
    trait_1 = Trait('chédiak-higashi syndrome', None, None)
    processed_trait_1 = process_trait(trait_1, zooma_filters, zooma_host, oxo_targets, oxo_distance, ols_query_fields,
                                    ols_field_list, target_ontology, preferred_ontologies)
    assert len(processed_trait_1.ols_result_list) == 7
    assert processed_trait_1.is_finished

    # Trait 2 finds nothing via OLS, so goes through Zooma as well and finds a high-confidence result
    trait_2 = Trait('isolated nonsyndromic congenital heart disease', None, None)
    processed_trait_2 = process_trait(trait_2, zooma_filters, zooma_host, oxo_targets, oxo_distance, ols_query_fields,
                                    ols_field_list, target_ontology, preferred_ontologies)
    assert len(processed_trait_2.ols_result_list) == 0
    assert len(processed_trait_2.zooma_result_list) == 1
    assert processed_trait_2.is_finished

    # Trait 3 finds results in OLS and Zooma, but finds no sufficiently good mappings
    trait_3 = Trait('aicardi-goutieres syndrome 5', None, None)
    processed_trait_3 = process_trait(trait_3, zooma_filters, zooma_host, oxo_targets, oxo_distance, ols_query_fields,
                                    ols_field_list, target_ontology, preferred_ontologies)
    assert len(processed_trait_3.ols_result_list) == 7
    assert len(processed_trait_3.zooma_result_list) == 6
    assert not processed_trait_3.is_finished


@pytest.mark.integration
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
    ols_query_fields = None
    ols_field_list = None

    # This should be marked as finished, as it's an exact string match with a term contained in the target ontology
    efo_trait = process_trait(Trait(trait_name, None, None), zooma_filters, zooma_host, oxo_targets, oxo_distance,
                              ols_query_fields, ols_field_list, target_ontology='efo', preferred_ontologies='')
    assert efo_trait.is_finished

    # This should not be marked as finished, even though Zooma finds an exact match in one of its ontologies, it's not
    # the requested target ontology and thus still needs to be curated
    hpo_trait = process_trait(Trait(trait_name, None, None), zooma_filters, zooma_host, oxo_targets, oxo_distance,
                              ols_query_fields, ols_field_list, target_ontology='hp', preferred_ontologies='')
    assert not hpo_trait.is_finished
