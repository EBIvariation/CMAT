import csv
import tempfile

import pytest
from cmat.trait_mapping.ols import EXACT_SYNONYM_KEY

from cmat.trait_mapping.ols_search import OlsMapping
from cmat.trait_mapping.ontology_mapping import MappingContext
from cmat.trait_mapping.output import output_trait_mapping, find_replacement_mapping, output_for_curation
from cmat.trait_mapping.trait import OntologyEntry, Trait


def test_output_trait_mapping():
    tempfile_path = tempfile.mkstemp()[1]
    with open(tempfile_path, "w", newline='') as mapping_file:
        mapping_writer = csv.writer(mapping_file, delimiter="\t")
        mapping_writer.writerow(["#clinvar_trait_name", "uri", "label"])

        test_trait = Trait('aprt deficiency, japanese type', '99999', 11)

        # Normally a set, but changed to a list for predictable output order in test
        test_trait.finished_mapping_set = [
            OntologyEntry('http://www.orpha.net/ORDO/Orphanet_976',
                          'Adenine phosphoribosyltransferase deficiency'),
            OntologyEntry('http://www.orpha.net/ORDO/Orphanet_977',
                          'Adenine phosphoribosyltransferase deficiency type A')
        ]

        output_trait_mapping(test_trait, mapping_writer)

    with open(tempfile_path, "rt", newline='') as mapping_file:
        mapping_reader = csv.reader(mapping_file, delimiter="\t")
        next(mapping_reader)
        assert ['aprt deficiency, japanese type',
                'http://www.orpha.net/ORDO/Orphanet_976',
                'Adenine phosphoribosyltransferase deficiency'] == next(mapping_reader)

        assert ['aprt deficiency, japanese type',
                'http://www.orpha.net/ORDO/Orphanet_977',
                'Adenine phosphoribosyltransferase deficiency type A'] == next(mapping_reader)


@pytest.mark.integration
def test_find_replacement_mapping():
    trait_name = 'genetic transient congenital hypothyroidism'
    target_ontology = 'efo'
    preferred_ontologies = ['mondo', 'hp']

    # Current in EFO - no replacement term
    assert find_replacement_mapping(
        trait_name, 'http://purl.obolibrary.org/obo/MONDO_0011792', target_ontology, preferred_ontologies
    ) == ''

    # Deprecated in EFO with current replacement term
    assert find_replacement_mapping(
        trait_name, 'http://www.ebi.ac.uk/efo/EFO_0000665', target_ontology, preferred_ontologies
    ) == 'http://purl.obolibrary.org/obo/MONDO_0037939|porphyria|PREVIOUS|TOKEN_MATCH_SYNONYM|EFO_CURRENT'

    # Deprecated in EFO but replacement is also deprecated, so use its replacement
    assert find_replacement_mapping(
        trait_name, 'http://www.orpha.net/ORDO/Orphanet_226316', target_ontology, preferred_ontologies
    ) == 'http://purl.obolibrary.org/obo/MONDO_0011792|thyroid dyshormonogenesis 6|PREVIOUS|TOKEN_MATCH_SYNONYM|EFO_CURRENT'


def test_output_for_curation():
    tempfile_path = tempfile.mkstemp()[1]
    with open(tempfile_path, "wt") as curation_file:
        curation_writer = csv.writer(curation_file, delimiter="\t")

        test_trait = Trait("transitional cell carcinoma of the bladder", '99999', 276)

        test_ols_result = OlsMapping(
            mapping_context=MappingContext('', 'efo', ['mondo', 'hp']),
            uri='http://purl.obolibrary.org/obo/HP_0006740',
            label='Transitional cell carcinoma of the bladder',
            exact_match=[],
            contained_match=['label'],
            token_match=['synonym'],
            in_target_ontology=False,
            in_preferred_ontology=True,
            is_current=False
        )
        test_trait.candidate_mappings = [test_ols_result]

        output_for_curation(test_trait, curation_writer, 'efo', ['mondo', 'hp'])

    with open(tempfile_path, "rt") as curation_file:
        curation_reader = csv.reader(curation_file, delimiter="\t")
        expected_record = [
            "transitional cell carcinoma of the bladder", "276", '', '', '', '', '',
            "http://purl.obolibrary.org/obo/HP_0006740|Transitional cell carcinoma of the bladder|OLS|CONTAINED_MATCH_LABEL|MONDO_HP_NOT_EFO"
        ]
        assert expected_record == next(curation_reader)


def test_output_for_curation_ordering():
    tempfile_path = tempfile.mkstemp()[1]
    with open(tempfile_path, "wt") as curation_file:
        curation_writer = csv.writer(curation_file, delimiter="\t")

        test_trait = Trait("hemoglobin s", '99999', 276)
        mapping_context = MappingContext('hemoglobin s', 'efo', ['mondo', 'hp'])
        test_trait.candidate_mappings = [
            # http://purl.obolibrary.org/obo/NCIT_C122123|Hemoglobin S Measurement|EXACT_MATCH_SYNONYM|NOT_MONDO_HP_EFO
            OlsMapping(
                mapping_context=mapping_context,
                uri='http://purl.obolibrary.org/obo/NCIT_C122123',
                label='Hemoglobin S Measurement',
                exact_match=[EXACT_SYNONYM_KEY],
                contained_match=[],
                token_match=[],
                in_target_ontology=False,
                in_preferred_ontology=False,
                is_current=False
            ),
            # http://www.ebi.ac.uk/efo/EFO_0009223|Hemoglobin S Measurement|EXACT_MATCH_SYNONYM|EFO_CURRENT
            OlsMapping(
                mapping_context=mapping_context,
                uri='http://www.ebi.ac.uk/efo/EFO_0009223',
                label='Hemoglobin S Measurement',
                exact_match=[EXACT_SYNONYM_KEY],
                contained_match=[],
                token_match=[],
                in_target_ontology=True,
                in_preferred_ontology=False,
                is_current=True
            )
        ]

        output_for_curation(test_trait, curation_writer, 'efo', ['mondo', 'hp'])

    with open(tempfile_path, "rt") as curation_file:
        curation_reader = csv.reader(curation_file, delimiter="\t")
        expected_record = [
            "hemoglobin s", "276", '', '', '', '',
            # The exact synonym match chosen for the dedicated column should be the one in EFO
            'http://www.ebi.ac.uk/efo/EFO_0009223|Hemoglobin S Measurement|OLS|EXACT_MATCH_SYNONYM|EFO_CURRENT',
            "http://purl.obolibrary.org/obo/NCIT_C122123|Hemoglobin S Measurement|OLS|EXACT_MATCH_SYNONYM|NOT_MONDO_HP_EFO"
        ]
        assert expected_record == next(curation_reader)
