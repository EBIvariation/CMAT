import csv
import tempfile

import cmat.trait_mapping.output as output
from cmat.trait_mapping.ols import OlsResult
from cmat.trait_mapping.trait import OntologyEntry, Trait
import cmat.trait_mapping.zooma as zooma


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

        output.output_trait_mapping(test_trait, mapping_writer)

    with open(tempfile_path, "rt", newline='') as mapping_file:
        mapping_reader = csv.reader(mapping_file, delimiter="\t")
        next(mapping_reader)
        assert ['aprt deficiency, japanese type',
                'http://www.orpha.net/ORDO/Orphanet_976',
                'Adenine phosphoribosyltransferase deficiency'] == next(mapping_reader)

        assert ['aprt deficiency, japanese type',
                'http://www.orpha.net/ORDO/Orphanet_977',
                'Adenine phosphoribosyltransferase deficiency type A'] == next(mapping_reader)


def test_get_non_efo_mapping():
    """If mapping is not in EFO, its `is_current` flag should *not* be checked, and the mapping
    *should* be selected for curation."""
    test_zooma_result = zooma.ZoomaResult(['http://purl.obolibrary.org/obo/HP_0001892'],
                                          'abnormal bleeding', 'HIGH', 'eva-clinvar')
    mapping = test_zooma_result.mapping_list[0]
    mapping.confidence = zooma.ZoomaConfidence.HIGH
    mapping.in_ontology = False
    mapping.is_current = False
    mapping.ontology_label = 'abnormal bleeding'
    mapping.source = 'eva-clinvar'
    mapping.uri = 'http://purl.obolibrary.org/obo/HP_0000483'
    assert [mapping] == output.get_mappings_for_curation([test_zooma_result], 'abnormal bleeding')


def test_get_obsolete_efo_mapping():
    """If mapping is in EFO, but is not current, it *should not* be selected for curation."""
    test_zooma_result = zooma.ZoomaResult(['http://www.orpha.net/ORDO/Orphanet_976'],
                                          'Adenine phosphoribosyltransferase deficiency',
                                          'HIGH', 'eva-clinvar')
    mapping = test_zooma_result.mapping_list[0]
    mapping.confidence = zooma.ZoomaConfidence.HIGH
    mapping.in_ontology = True
    mapping.is_current = False
    mapping.ontology_label = "Adenine phosphoribosyltransferase deficiency"
    mapping.source = 'eva-clinvar'
    mapping.uri = 'http://www.orpha.net/ORDO/Orphanet_976'
    assert [] == output.get_mappings_for_curation([test_zooma_result], 'adenine phosphoribosyltransferase deficiency')


def test_get_current_efo_mapping():
    """If mapping is in EFO and is current, ii *should* be selected for curation."""
    test_zooma_result = zooma.ZoomaResult(['http://purl.obolibrary.org/obo/MONDO_0008091'],
                                          'Abnormal neutrophil chemotactic response',
                                          'MEDIUM', 'eva-clinvar')
    mapping = test_zooma_result.mapping_list[0]
    mapping.confidence = zooma.ZoomaConfidence.HIGH
    mapping.in_ontology = True
    mapping.is_current = True
    mapping.ontology_label = "Abnormal neutrophil chemotactic response"
    mapping.source = 'eva-clinvar'
    mapping.uri = 'http://purl.obolibrary.org/obo/MONDO_0008091'
    assert [mapping] == output.get_mappings_for_curation([test_zooma_result], 'Abnormal neutrophil chemotactic response')


def test_get_current_efo_nonexact_mapping():
    """If mapping is in EFO and is current but is not an exact match, it *should* be selected for curation."""
    test_zooma_result = zooma.ZoomaResult(['http://purl.obolibrary.org/obo/MONDO_0008091'],
                                          'Abnormal neutrophil chemotactic response',
                                          'MEDIUM', 'eva-clinvar')
    mapping = test_zooma_result.mapping_list[0]
    mapping.confidence = zooma.ZoomaConfidence.HIGH
    mapping.in_ontology = True
    mapping.is_current = True
    mapping.ontology_label = "Abnormal neutrophil chemotactic response"
    mapping.source = 'eva-clinvar'
    mapping.uri = 'http://purl.obolibrary.org/obo/MONDO_0008091'
    assert [] == output.get_mappings_for_curation([test_zooma_result], 'neutrophil chemotactic response')


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

        output.output_for_curation(test_trait, curation_writer, 'efo', ['mondo', 'hp'])

    with open(tempfile_path, "rt") as curation_file:
        curation_reader = csv.reader(curation_file, delimiter="\t")
        expected_record = [
            "transitional cell carcinoma of the bladder", "276", '',
            "http://purl.obolibrary.org/obo/HP_0006740|Transitional cell carcinoma of the bladder|CONTAINED_MATCH_LABEL|MONDO_HP_NOT_EFO"
        ]
        assert expected_record == next(curation_reader)
