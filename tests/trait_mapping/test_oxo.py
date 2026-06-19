from unittest.mock import patch

import pytest
import requests_mock

import cmat.trait_mapping.oxo as oxo
from cmat.trait_mapping.ols import OLS_BASE_URL

import resources.test_oxo_data as test_oxo_data
from cmat.trait_mapping.ontology_mapping import MappingContext


class TestUriToOxoFormat:
    def test_ordo(self):
        assert oxo.uri_to_oxo_format("http://www.orpha.net/ORDO/Orphanet_140162") == "Orphanet:140162"

    def test_omim(self):
        assert oxo.uri_to_oxo_format("http://purl.obolibrary.org/obo/OMIM_314580") == "OMIM:314580"
        assert oxo.uri_to_oxo_format("http://identifiers.org/omim/314580") == "OMIM:314580"
        assert oxo.uri_to_oxo_format("http://www.omim.org/entry/314580") == "OMIM:314580"

    def test_efo(self):
        assert oxo.uri_to_oxo_format("http://www.ebi.ac.uk/efo/EFO_0000313") == "EFO:0000313"

    def test_mesh(self):
        assert oxo.uri_to_oxo_format("http://purl.obolibrary.org/obo/MESH_D002277") == "MeSH:D002277"
        assert oxo.uri_to_oxo_format("http://identifiers.org/mesh/D002277") == "MeSH:D002277"

    def test_hp(self):
        assert oxo.uri_to_oxo_format("http://purl.obolibrary.org/obo/HP_0030731") == "HP:0030731"

    def test_mondo(self):
        assert oxo.uri_to_oxo_format("http://purl.obolibrary.org/obo/MONDO_0019531") == "MONDO:0019531"

    def test_nonexistent(self):
        assert oxo.uri_to_oxo_format("not_a_real_uri") is None


class TestBuildOxoPayload:
    def test_build_payload(self):
        id_list = ["OMIM:314580", "MeSH:D002277"]
        target_list = ["Orphanet", "efo", "hp"]
        distance = 3
        assert oxo.build_oxo_payload(id_list, target_list, distance) == {"ids": id_list, "mappingTarget": target_list,
                                                                         "distance": distance}


class TestGetOxoResultsFromResponse:
    def test_get_oxo_results_from_response(self):
        with requests_mock.mock() as m:
            m.get(f"{OLS_BASE_URL}/classes?iri=http://www.orpha.net/ORDO/Orphanet_660",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.orphanet_660_ols_terms_json)

            m.get(
                f"{OLS_BASE_URL}/ontologies/efo/classes/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_660",
                json={'message': 'Resource not found', 'timestamp': 1502441846181,
                      'exception': 'org.springframework.data.rest.webmvc.ResourceNotFoundException', 'status': 404,
                      'error': 'Not Found',
                      'path': '/ols4/api/ontologies/efo/terms/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_660'},
                status_code=404)

            m.get(f"{OLS_BASE_URL}/classes?iri=http://www.orpha.net/ORDO/Orphanet_3164",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.orphanet_3164_ols_terms_json)

            m.get(f"{OLS_BASE_URL}/ontologies/efo/classes/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_3164",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.orphanet_3164_ols_efo_json)

            m.get(f"{OLS_BASE_URL}/classes?iri=http://purl.obolibrary.org/obo/HP_0001537",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.hp_0001537_ols_terms_json)

            oxo_response = {'_embedded': {'searchResults': [{'curie': 'HP:0001537', '_links': {'self': {'href': 'https://www.ebi.ac.uk/spot/oxo/api/terms/HP:0001537'}, 'mappings': {'href': 'https://www.ebi.ac.uk/spot/oxo/api/mappings?fromId=HP:0001537'}}, 'label': 'Umbilical hernia', 'querySource': None, 'queryId': 'HP:0001537', 'mappingResponseList': [{'curie': 'Orphanet:660', 'targetPrefix': 'Orphanet', 'distance': 1, 'sourcePrefixes': ['ONTONEO', 'Orphanet', 'DOID', 'UMLS'], 'label': 'Omphalocele'}, {'curie': 'Orphanet:3164', 'targetPrefix': 'Orphanet', 'distance': 1, 'sourcePrefixes': ['ONTONEO', 'EFO', 'Orphanet', 'DOID'], 'label': 'Omphalocele syndrome, Shprintzen-Goldberg type'}]}]}, 'page': {'totalPages': 1, 'size': 1000, 'number': 0, 'totalElements': 1}, '_links': {'self': {'href': 'https://www.ebi.ac.uk/spot/oxo/api/search'}}}
            mapping_context = MappingContext('omphalocele', 'efo', [])
            expected_oxo_results = [
                oxo.OxoMapping(
                    mapping_context=mapping_context,
                    uri="http://www.orpha.net/ORDO/Orphanet_660",
                    label="Omphalocele",
                    distance=1,
                    query_id="http://purl.obolibrary.org/obo/HP_0001537"),
                oxo.OxoMapping(
                    mapping_context=mapping_context,
                    uri="http://www.orpha.net/ORDO/Orphanet_3164",
                    label="Omphalocele syndrome, Shprintzen-Goldberg type",
                    distance=1,
                    query_id="http://purl.obolibrary.org/obo/HP_0001537")]

            assert oxo.get_oxo_results_from_response(mapping_context, oxo_response, 1) == expected_oxo_results

    @pytest.mark.integration
    @pytest.mark.skip(reason="OxO frequently down")
    def test_get_oxo_results(self):
        id_list = ["OMIM:314580", "MeSH:D002277"]
        target_list = ["Orphanet", "efo", "hp"]
        results = oxo.get_oxo_results(id_list, target_list, distance=1)
        assert len(results) == 2
        assert len(results[0].mapping_list) == 2
        assert len(results[1].mapping_list) == 2


class TestOxoMapping:

    def test_oxo_mapping_sorting(self):
        mapping_context = MappingContext('trait', 'efo', ['mondo', 'hp'])
        # Base mapping: preferred not target and distance 2
        mapping_1 = oxo.OxoMapping(mapping_context, 'uri_1', 'trait', 2, 'query_id')
        # Mapping with a better source but worse distance
        mapping_2 = oxo.OxoMapping(mapping_context, 'uri_2', 'trait', 3, 'query_id')
        # Mapping with a worse source but better distance
        mapping_3 = oxo.OxoMapping(mapping_context, 'uri_3', 'trait', 1, 'query_id')
        # Mapping with same source but better distance
        mapping_4 = oxo.OxoMapping(mapping_context, 'uri_4', 'trait', 1, 'query_id')

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
