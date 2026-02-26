import os

import pytest

from cmat.output_generation.clinvar_to_evidence_strings import load_ontology_mapping
from cmat.trait_mapping.trait_processing import process_trait
from cmat.trait_mapping.trait import Trait

test_dir = os.path.dirname(__file__)
mapping_file = os.path.join(test_dir, 'resources', 'string_to_ontology_mappings.tsv')
previous_mappings = load_ontology_mapping(mapping_file)[0]

# TODO rewrite and add more tests
@pytest.mark.integration
class TestProcessTrait:
    # Use all default filters
    zooma_filters = {'ontologies': 'efo,ordo,hp,mondo',
                     'required': 'cttv,eva-clinvar,clinvar-xrefs,gwas',
                     'preferred': 'eva-clinvar,cttv,gwas,clinvar-xrefs'}
    oxo_targets = ['Orphanet', 'efo', 'hp', 'mondo']
    oxo_distance = 3
    ols_query_fields = 'label,synonym'
    ols_field_list = 'iri,label,ontology_name,synonym'
    target_ontology = 'EFO'
    preferred_ontologies = ['mondo', 'hp']

    def run_process_trait(self, trait):
        return process_trait(trait, previous_mappings, self.zooma_filters, self.oxo_targets, self.oxo_distance,
                             self.ols_query_fields, self.ols_field_list, self.target_ontology,
                             self.preferred_ontologies)

    def test_ols_exact_match(self):
        # Only goes through OLS as it finds an exact match in EFO
        trait = Trait('chédiak-higashi syndrome', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.ols_result_list) == 8
        assert processed_trait.is_finished

    # def test_zooma_high_confidence(self):
    #     # Finds nothing exact via OLS, so goes through Zooma as well and finds a high-confidence result
    #     trait = Trait('11p partial monosomy syndrome', None, None)
    #     processed_trait = self.run_process_trait(trait)
    #     assert len(processed_trait.ols_result_list) == 6
    #     assert len(processed_trait.zooma_result_list) == 2
    #     assert processed_trait.is_finished

    def test_not_finished(self):
        # No sufficiently good mappings in OLS or Zooma
        trait = Trait('aicardi-goutieres syndrome 99', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.ols_result_list) == 0
        assert len(processed_trait.zooma_result_list) == 19
        assert not processed_trait.is_finished

    def test_ols_exact_ascii_match(self):
        # Search should be agnostic to accents and other non-ASCII characters
        trait = Trait('pelger-huët anomaly', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.ols_result_list) == 11
        assert processed_trait.is_finished
        assert {m.uri for m in processed_trait.finished_mapping_set} == {'http://www.ebi.ac.uk/efo/EFO_1001093'}

    def test_multiple_mappings(self):
        # Multiple mappings from OLS
        trait = Trait('albinism', None, None)
        processed_trait = self.run_process_trait(trait)
        assert processed_trait.is_finished
        assert len(processed_trait.finished_mapping_set) == 2


@pytest.mark.integration
def test_process_trait_zooma_exact_match():
    # Exact match with MONDO:0009061 (in EFO and Mondo)
    trait_name = 'Cystic Fibrosis'
    # Use our default Zooma filters
    zooma_filters = {'ontologies': 'efo,ordo,hp,mondo',
                     'required': 'cttv,eva-clinvar,clinvar-xrefs,gwas',
                     'preferred': 'eva-clinvar,cttv,gwas,clinvar-xrefs'}
    # Don't use OxO
    oxo_targets = []
    oxo_distance = 0
    # Don't use OLS
    ols_query_fields = None
    ols_field_list = None

    # This should be marked as finished, as it's an exact string match with a term contained in the target ontology
    efo_trait = process_trait(Trait(trait_name, None, None), previous_mappings, zooma_filters,
                              oxo_targets, oxo_distance, ols_query_fields, ols_field_list, target_ontology='efo',
                              preferred_ontologies=[])
    assert efo_trait.is_finished

    # This should not be marked as finished, even though Zooma finds an exact match in one of its ontologies, it's not
    # the requested target ontology and thus still needs to be curated
    hpo_trait = process_trait(Trait(trait_name, None, None), previous_mappings, zooma_filters,
                              oxo_targets, oxo_distance, ols_query_fields, ols_field_list, target_ontology='hp',
                              preferred_ontologies=[])
    assert not hpo_trait.is_finished
