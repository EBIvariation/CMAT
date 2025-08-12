import cmat.trait_mapping.trait as trait
import cmat.trait_mapping.zooma as zooma
import cmat.trait_mapping.oxo as oxo
from cmat.trait_mapping.ols import OlsResult


def test_is_finished_true():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)
    test_trait.finished_mapping_set.add(trait.OntologyEntry('http://www.orpha.net/ORDO/Orphanet_976',
                                                            'Adenine phosphoribosyltransferase deficiency'))
    assert test_trait.is_finished

def test_is_finished_false():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)
    assert not test_trait.is_finished


def test_process_zooma_result():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)

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

    test_trait.zooma_result_list.append(test_zooma_result)

    test_trait.process_zooma_results()
    assert 1 == len(test_trait.finished_mapping_set)


def test_process_oxo_mappings():
    test_trait = trait.Trait('congenital cystic disease of liver', '99999', 11)

    test_oxo_result = oxo.OxOResult('HP:0006706', 'Cystic liver disease', 'HP:0006706')

    test_oxo_mapping_1 = oxo.OxOMapping('Isolated polycystic liver disease', 'Orphanet:2924', 2,
                                        'HP:0006706')
    test_oxo_mapping_1.in_ontology = True
    test_oxo_mapping_1.is_current = True

    test_oxo_mapping_2 = oxo.OxOMapping('cystic liver disease', 'EFO:1001505', 1, 'HP:0006706')
    test_oxo_mapping_2.in_ontology = True
    test_oxo_mapping_2.is_current = True

    test_oxo_result.mapping_list = [test_oxo_mapping_1, test_oxo_mapping_2]

    test_trait.oxo_result_list.append(test_oxo_result)

    test_trait.process_oxo_mappings()

    assert 1 == len(test_trait.finished_mapping_set)


def test_process_ols_mappings():
    test_trait = trait.Trait('Hereditary factor VIII deficiency disease', '99999', 11)
    ols_results = [
        OlsResult(
            uri='http://snomed.info/id/28293008',
            label='Hereditary factor VIII deficiency disease',
            ontology='snomed',
            full_exact_match=['label'],
            contained_match=[],
            token_match=[],
            in_target_ontology=False, in_preferred_ontology=False, is_current=False
        ),
        OlsResult(
            uri='http://purl.obolibrary.org/obo/MONDO_0010602',
            label='hemophilia A',
            ontology='mondo',
            full_exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
            contained_match=[],
            token_match=['label'],
            in_target_ontology=False, in_preferred_ontology=True, is_current=False
        ),
        OlsResult(
            uri='http://purl.obolibrary.org/obo/MONDO_0010602',
            label='hemophilia A',
            ontology='efo',
            full_exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
            contained_match=[],
            token_match=['label'],
            in_target_ontology=True, in_preferred_ontology=False, is_current=True
        )
    ]
    test_trait.ols_result_list = ols_results

    test_trait.process_ols_results()

    # MONDO_0010602 in Mondo is removed as there is already MONDO_0010602 in EFO
    assert len(test_trait.ols_result_list) == 2
    assert {r.uri for r in test_trait.ols_result_list} == {'http://snomed.info/id/28293008', 'http://purl.obolibrary.org/obo/MONDO_0010602'}
    assert {r.ontology for r in test_trait.ols_result_list} == {'snomed', 'efo'}
