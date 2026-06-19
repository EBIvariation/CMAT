from unittest.mock import patch

import cmat.trait_mapping.zooma as zooma
from cmat.trait_mapping.ols import OLS_BASE_URL
from cmat.trait_mapping.ontology_mapping import MappingContext
from cmat.trait_mapping.zooma import ZoomaMapping


def test_build_zooma_query():
    trait_name = 'gastric cancer susceptibility after h. pylori infection'
    filters = {'required': 'cttv,eva-clinvar,gwas',
               'preferred': 'eva-clinvar,cttv,gwas',
               'ontologies': 'efo,ordo,hp'}

    expected_url = 'https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate?propertyValue=gastric cancer susceptibility after h. pylori infection&filter=required:[cttv,eva-clinvar,gwas],ontologies:[efo,ordo,hp],preferred:[eva-clinvar,cttv,gwas]'

    assert zooma.build_zooma_query(trait_name, filters) == expected_url


def test_get_zooma_results_for_trait():
    mapping_context = MappingContext('abnormal bleeding', 'efo', ['mondo', 'hp'])
    zooma_response_list = [{'confidence': 'HIGH', 'semanticTags': ['http://purl.obolibrary.org/obo/HP_0001892'],
                            'provenance': {'source': {'uri': 'http://www.ebi.ac.uk/spot/zooma', 'type': 'DATABASE',
                                                      'name': 'zooma'}, 'generatedDate': 1502287637052,
                                           'accuracy': None, 'generator': 'ZOOMA', 'annotator': 'ZOOMA',
                                           'evidence': 'ZOOMA_INFERRED_FROM_CURATED',
                                           'annotationDate': 1502287637052}, '_links': {'olslinks': [
            {'href': f'{OLS_BASE_URL}/api/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FHP_0001892',
             'semanticTag': 'http://purl.obolibrary.org/obo/HP_0001892'}]}, 'annotatedBiologicalEntities': [],
                            'annotatedProperty': {
                                'uri': 'http://rdf.ebi.ac.uk/resource/zooma/8EAA9C1095AD18A90D557D7086084B64',
                                'propertyValue': 'abnormal bleeding', 'propertyType': 'disease'}, 'uri': None,
                            'derivedFrom': {'semanticTags': ['http://purl.obolibrary.org/obo/HP_0001892'],
                                            'provenance': {
                                                'source': {'uri': 'http://www.ebi.ac.uk/eva', 'type': 'DATABASE',
                                                           'name': 'eva-clinvar'}, 'generatedDate': 1502442040000,
                                                'accuracy': 'NOT_SPECIFIED',
                                                'generator': 'http://www.ebi.ac.uk/eva', 'annotator': 'eva',
                                                'evidence': 'MANUAL_CURATED', 'annotationDate': -61612629390000},
                                            '_links': {'olslinks': [
                                                {'href': 'http://purl.obolibrary.org/obo/HP_0001892',
                                                 'semanticTag': 'http://purl.obolibrary.org/obo/HP_0001892'}]},
                                            'annotatedBiologicalEntities': [], 'annotatedProperty': {
                                    'uri': 'http://rdf.ebi.ac.uk/resource/zooma/8EAA9C1095AD18A90D557D7086084B64',
                                    'propertyValue': 'abnormal bleeding', 'propertyType': 'disease'},
                                            'uri': 'http://rdf.ebi.ac.uk/resource/zooma/eva-clinvar/2D66457AE8F4E9A31CDD27E66F5B4607',
                                            'replaces': [], 'replacedBy': []}, 'replaces': [], 'replacedBy': []}]
    expected_zooma_result = zooma.ZoomaMapping(mapping_context,'http://purl.obolibrary.org/obo/HP_0001892',
                                              'HIGH', 'eva-clinvar')
    expected_mappings = [expected_zooma_result]

    assert zooma.get_zooma_results_for_trait(mapping_context, zooma_response_list) == expected_mappings


def test_zooma_mapping_sorting():
    mapping_context = MappingContext('trait', 'efo', ['mondo', 'hp'])
    # Base mapping: preferred not target and good confidence
    mapping_1 = ZoomaMapping(mapping_context, 'uri_1', 'good', 'source')
    # Mapping with a better source but lower confidence
    mapping_2 = ZoomaMapping(mapping_context, 'uri_2', 'low', 'source')
    # Mapping with a worse source but higher confidence
    mapping_3 = ZoomaMapping(mapping_context, 'uri_3', 'high', 'source')
    # Mapping with same source but higher confidence
    mapping_4 = ZoomaMapping(mapping_context, 'uri_4', 'high', 'source')

    def mock_is_in_ontologies(uri, mapping_context):
        # Returns is_in_target, is_in_preferred
        if uri == 'uri_1':
            return False, True
        if uri == 'uri_2':
            return True, False
        if uri == 'uri_3':
            return False, False
        if uri == 'uri_4':
            return False, True
        return NotImplemented

    with patch('cmat.trait_mapping.ontology_mapping.get_is_in_ontologies') as m_get_is_in_ontologies, \
        patch('cmat.trait_mapping.ontology_mapping.is_current_and_in_ontology') as m_is_current_and_in_ontology, \
        patch('cmat.trait_mapping.ontology_mapping.get_label_and_synonyms_from_ols') as m_get_label_and_synonyms_from_ols:
        m_get_is_in_ontologies.side_effect = mock_is_in_ontologies
        m_is_current_and_in_ontology.return_value = True  # only called if mapping is in target ontology
        m_get_label_and_synonyms_from_ols.return_value = ('trait', [])  # all match types are exact label

        mappings = [mapping_1, mapping_2, mapping_3, mapping_4]
        result = sorted(mappings)
        assert result == [mapping_2, mapping_4, mapping_1, mapping_3]
