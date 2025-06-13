import cmat.trait_mapping.zooma as zooma
from cmat.trait_mapping.ols import OLS_BASE_URL


def test_build_zooma_query():
    trait_name = 'gastric cancer susceptibility after h. pylori infection'
    filters = {'required': 'cttv,eva-clinvar,gwas',
               'preferred': 'eva-clinvar,cttv,gwas',
               'ontologies': 'efo,ordo,hp'}
    zooma_host = 'https://www.ebi.ac.uk'

    expected_url = 'https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate?propertyValue=gastric cancer susceptibility after h. pylori infection&filter=required:[cttv,eva-clinvar,gwas],ontologies:[efo,ordo,hp],preferred:[eva-clinvar,cttv,gwas]'

    assert zooma.build_zooma_query(trait_name, filters, zooma_host) == expected_url


def test_get_zooma_results_for_trait():
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
    expected_zooma_result = zooma.ZoomaResult(['http://purl.obolibrary.org/obo/HP_0001892'],
                                              'abnormal bleeding', 'HIGH', 'eva-clinvar')
    entry = expected_zooma_result.mapping_list[0]
    entry.confidence = zooma.ZoomaConfidence.HIGH
    entry.in_ontology = False
    entry.is_current = False
    entry.ontology_label = ""
    entry.source = 'eva-clinvar'
    entry.uri = 'http://purl.obolibrary.org/obo/HP_0000483'

    expected_mappings = [expected_zooma_result]

    assert zooma.get_zooma_results_for_trait(zooma_response_list) == expected_mappings
