import csv
import tempfile

import pytest
from cmat.trait_mapping import zooma, oxo

from cmat.trait_mapping.ols import OlsResult
from cmat.trait_mapping.output import output_trait_mapping, find_replacement_mapping, output_for_curation, \
    get_zooma_mappings, to_mapping_string, get_oxo_mappings
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


def test_get_zooma_mappings():
    test_zooma_result = zooma.ZoomaResult(['http://www.orpha.net/ORDO/Orphanet_976'],
                                          'Adenine phosphoribosyltransferase deficiency',
                                          'HIGH', 'eva-clinvar')
    entry = test_zooma_result.mapping_list[0]
    entry.confidence = zooma.ZoomaConfidence.HIGH
    entry.in_ontology = True
    entry.is_current = True
    entry.ontology_label = "Adenine phosphoribosyltransferase deficiency"
    entry.source = 'eva-clinvar'
    entry.uri = 'http://www.orpha.net/ORDO/Orphanet_976'
    high_conf_mappings, exact_mappings = get_zooma_mappings([test_zooma_result], 'aprt deficiency, japanese type',
                                                            'efo', ['mondo', 'hp'])
    assert len(high_conf_mappings) == 1
    assert len(exact_mappings) == 0


def test_get_oxo_mappings():
    test_oxo_result = oxo.OxOResult('HP:0006706', 'Cystic liver disease', 'HP:0006706')

    test_oxo_mapping_1 = oxo.OxOMapping('Isolated polycystic liver disease', 'Orphanet:2924', 2,
                                        'HP:0006706')
    test_oxo_mapping_1.in_ontology = True
    test_oxo_mapping_1.is_current = True

    test_oxo_mapping_2 = oxo.OxOMapping('cystic liver disease', 'EFO:1001505', 1, 'HP:0006706')
    test_oxo_mapping_2.in_ontology = True
    test_oxo_mapping_2.is_current = True

    test_oxo_result.mapping_list = [test_oxo_mapping_1, test_oxo_mapping_2]

    dist_one_mappings, exact_mappings = get_oxo_mappings([test_oxo_result], 'congenital cystic disease of liver', 'efo',
                                                         ['mondo', 'hp'])

    assert len(dist_one_mappings) == 1
    assert len(exact_mappings) == 0


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
    ) == 'http://purl.obolibrary.org/obo/MONDO_0037939|porphyria|TOKEN_MATCH_SYNONYM|EFO_CURRENT'

    # Deprecated in EFO but replacement is also deprecated, so use its replacement
    assert find_replacement_mapping(
        trait_name, 'http://www.orpha.net/ORDO/Orphanet_226316', target_ontology, preferred_ontologies
    ) == 'http://purl.obolibrary.org/obo/MONDO_0011792|thyroid dyshormonogenesis 6|TOKEN_MATCH_SYNONYM|MONDO_HP_NOT_EFO'


def test_to_mapping_string():
    result = to_mapping_string('http://www.orpha.net/ORDO/Orphanet_976', 'aprt deficiency, japanese type', 'efo',
                               ['mondo', 'hp'])
    assert result == 'http://www.orpha.net/ORDO/Orphanet_976|Adenine phosphoribosyltransferase deficiency|NO_MATCH|EFO_OBSOLETE'


def test_output_for_curation():
    tempfile_path = tempfile.mkstemp()[1]
    with open(tempfile_path, "wt") as curation_file:
        curation_writer = csv.writer(curation_file, delimiter="\t")

        test_trait = Trait("transitional cell carcinoma of the bladder", '99999', 276)

        test_ols_result = OlsResult(
            uri='http://purl.obolibrary.org/obo/HP_0006740',
            label='Transitional cell carcinoma of the bladder',
            ontology=None,  # not needed for output
            full_exact_match=[],
            contained_match=['label'],
            token_match=['synonym'],
            in_target_ontology=False,
            in_preferred_ontology=True,
            is_current=False
        )
        test_trait.ols_result_list = [test_ols_result]

        output_for_curation(test_trait, curation_writer, 'efo', ['mondo', 'hp'])

    with open(tempfile_path, "rt") as curation_file:
        curation_reader = csv.reader(curation_file, delimiter="\t")
        expected_record = [
            "transitional cell carcinoma of the bladder", "276", '', '', '', '', '', '', '',
            "http://purl.obolibrary.org/obo/HP_0006740|Transitional cell carcinoma of the bladder|CONTAINED_MATCH_LABEL|MONDO_HP_NOT_EFO"
        ]
        assert expected_record == next(curation_reader)
