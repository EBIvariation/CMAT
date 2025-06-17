import requests_mock

import cmat.trait_mapping.oxo as oxo
from cmat.trait_mapping.ols import OLS_BASE_URL

import resources.test_oxo_data as test_oxo_data


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
            m.get(f"{OLS_BASE_URL}/terms?iri=http://www.orpha.net/ORDO/Orphanet_660",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.orphanet_660_ols_terms_json)

            m.get(
                f"{OLS_BASE_URL}/ontologies/efo/terms/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_660",
                json={'message': 'Resource not found', 'timestamp': 1502441846181,
                      'exception': 'org.springframework.data.rest.webmvc.ResourceNotFoundException', 'status': 404,
                      'error': 'Not Found',
                      'path': '/ols4/api/ontologies/efo/terms/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_660'},
                status_code=404)

            m.get(f"{OLS_BASE_URL}/terms?iri=http://www.orpha.net/ORDO/Orphanet_3164",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.orphanet_3164_ols_terms_json)

            m.get(f"{OLS_BASE_URL}/ontologies/efo/terms/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_3164",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.orphanet_3164_ols_efo_json)

            m.get(f"{OLS_BASE_URL}/terms?iri=http://purl.obolibrary.org/obo/HP_0001537",
                  json=test_oxo_data.TestGetOxoResultsFromResponseData.hp_0001537_ols_terms_json)

            oxo_response = {'_embedded': {'searchResults': [{'curie': 'HP:0001537', '_links': {'self': {'href': 'https://www.ebi.ac.uk/spot/oxo/api/terms/HP:0001537'}, 'mappings': {'href': 'https://www.ebi.ac.uk/spot/oxo/api/mappings?fromId=HP:0001537'}}, 'label': 'Umbilical hernia', 'querySource': None, 'queryId': 'HP:0001537', 'mappingResponseList': [{'curie': 'Orphanet:660', 'targetPrefix': 'Orphanet', 'distance': 3, 'sourcePrefixes': ['ONTONEO', 'Orphanet', 'DOID', 'UMLS'], 'label': 'Omphalocele'}, {'curie': 'Orphanet:3164', 'targetPrefix': 'Orphanet', 'distance': 3, 'sourcePrefixes': ['ONTONEO', 'EFO', 'Orphanet', 'DOID'], 'label': 'Omphalocele syndrome, Shprintzen-Goldberg type'}]}]}, 'page': {'totalPages': 1, 'size': 1000, 'number': 0, 'totalElements': 1}, '_links': {'self': {'href': 'https://www.ebi.ac.uk/spot/oxo/api/search'}}}
            expected_oxo_result = oxo.OxOResult("HP:0001537", "Umbilical hernia", "HP:0001537")
            expected_oxo_result.mapping_list = [oxo.OxOMapping("Omphalocele", "Orphanet:660", 3, "HP:0001537"),
                                                oxo.OxOMapping("Omphalocele syndrome, Shprintzen-Goldberg type", "Orphanet:3164", 3, "HP:0001537")]
            expected_oxo_results = [expected_oxo_result]

            assert oxo.get_oxo_results_from_response(oxo_response) == expected_oxo_results
