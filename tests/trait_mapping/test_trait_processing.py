import os

import pytest

from cmat.trait_mapping.ols_search import OlsMapping
from cmat.trait_mapping.ontology_mapping import PreviousMapping, ClinVarXrefMapping
from cmat.trait_mapping.trait_processing import process_trait
from cmat.trait_mapping.trait import Trait
from cmat.trait_mapping.utils import load_ontology_mapping
from cmat.trait_mapping.zooma import ZoomaMapping

test_dir = os.path.dirname(__file__)
mapping_file = os.path.join(test_dir, 'resources', 'string_to_ontology_mappings.tsv')
previous_mappings = load_ontology_mapping(mapping_file)[0]


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

    def get_mapping_types(self, trait):
        return set(type(m) for m in trait.candidate_mappings)

    def test_ols_exact_match(self):
        # Only goes through OLS as it finds an exact match in EFO
        trait = Trait('chédiak-higashi syndrome', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.candidate_mappings) == 8
        assert self.get_mapping_types(processed_trait) == {OlsMapping}
        assert processed_trait.is_finished

    def test_previous_mapping(self):
        # Finds nothing exact via OLS, so checks previous mappings and finds a current result
        trait = Trait('11p partial monosomy syndrome', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.candidate_mappings) == 7
        assert self.get_mapping_types(processed_trait) == {OlsMapping, PreviousMapping}
        assert processed_trait.is_finished

    def test_not_finished(self):
        # No sufficiently good mappings in OLS or Zooma
        trait = Trait('aicardi-goutieres syndrome 99', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.candidate_mappings) == 44
        assert self.get_mapping_types(processed_trait) == {ZoomaMapping}
        assert not processed_trait.is_finished

    def test_ols_exact_ascii_match(self):
        # Search should be agnostic to accents and other non-ASCII characters
        trait = Trait('pelger-huët anomaly', None, None)
        processed_trait = self.run_process_trait(trait)
        assert len(processed_trait.candidate_mappings) == 20
        assert processed_trait.is_finished
        assert {m.uri for m in processed_trait.finished_mapping_set} == {'http://purl.obolibrary.org/obo/MONDO_0008214'}

    def test_multiple_mappings(self):
        # Multiple mappings from OLS
        trait = Trait('albinism', None, None)
        processed_trait = self.run_process_trait(trait)
        assert processed_trait.is_finished
        assert len(processed_trait.finished_mapping_set) == 2

        # Multiple mappings from previous
        trait = Trait('coronary artery disease/myocardial infarction', None, None)
        processed_trait = self.run_process_trait(trait)
        assert processed_trait.is_finished
        assert len(processed_trait.finished_mapping_set) == 2

    def test_with_clinvar_xrefs(self):
        xrefs = ['http://identifiers.org/medgen/C3150169']
        trait = Trait('frontotemporal lobar degeneration with tdp43 inclusions, tardbp-related', None, None, xrefs)
        processed_trait = self.run_process_trait(trait)
        assert not processed_trait.is_finished
        # TODO currently this contains the xref from both Zooma and ClinVar, should deduplicate...
        assert len(processed_trait.candidate_mappings) == 3
        for mapping in processed_trait.candidate_mappings:
            if isinstance(mapping, ClinVarXrefMapping):
                assert mapping.uri == xrefs[0]
