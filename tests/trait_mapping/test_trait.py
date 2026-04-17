import cmat.trait_mapping.trait as trait


def test_is_finished_true():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)
    test_trait.finished_mapping_set.add(trait.OntologyEntry('http://www.orpha.net/ORDO/Orphanet_976',
                                                            'Adenine phosphoribosyltransferase deficiency'))
    assert test_trait.is_finished


def test_is_finished_false():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)
    assert not test_trait.is_finished


# def test_process_ols_mappings():
#     test_trait = trait.Trait('Hereditary factor VIII deficiency disease', '99999', 11)
#     ols_results = [
#         OlsResult(
#             uri='http://snomed.info/id/28293008',
#             label='Hereditary factor VIII deficiency disease',
#             ontology='snomed',
#             full_exact_match=['label'],
#             contained_match=[],
#             token_match=[],
#             in_target_ontology=False, in_preferred_ontology=False, is_current=False
#         ),
#         OlsResult(
#             uri='http://purl.obolibrary.org/obo/MONDO_0010602',
#             label='hemophilia A',
#             ontology='mondo',
#             full_exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
#             contained_match=[],
#             token_match=['label'],
#             in_target_ontology=False, in_preferred_ontology=True, is_current=False
#         ),
#         OlsResult(
#             uri='http://purl.obolibrary.org/obo/MONDO_0010602',
#             label='hemophilia A',
#             ontology='efo',
#             full_exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
#             contained_match=[],
#             token_match=['label'],
#             in_target_ontology=True, in_preferred_ontology=False, is_current=True
#         )
#     ]
#     test_trait.ols_result_list = ols_results
#
#     test_trait.process_ols_results()
#
#     # MONDO_0010602 in Mondo is removed as there is already MONDO_0010602 in EFO
#     assert len(test_trait.ols_result_list) == 2
#     assert {r.uri for r in test_trait.ols_result_list} == {'http://snomed.info/id/28293008', 'http://purl.obolibrary.org/obo/MONDO_0010602'}
#     assert {r.ontology for r in test_trait.ols_result_list} == {'snomed', 'efo'}
#
#
# def test_process_previous_mappings():
#     test_trait = trait.Trait('Hereditary factor VIII deficiency disease', '99999', 11)
#     test_trait.previous_mapping_list = [
#         ('http://purl.obolibrary.org/obo/MONDO_0010602', 'hemophilia A'),
#         ('http://www.orpha.net/ORDO/Orphanet_98878', 'hemophilia A')
#     ]
#     test_trait.process_previous_mappings('efo')
#     assert test_trait.is_finished
#     assert len(test_trait.finished_mapping_set) == 1
