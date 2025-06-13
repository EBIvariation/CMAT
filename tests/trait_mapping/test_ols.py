import requests_mock

import cmat.trait_mapping.ols as ols
import resources.test_ols_data as test_ols_data


def test_get_ontology_label_from_ols():
    url = "http://www.orpha.net/ORDO/Orphanet_199318"
    ols_request_url = ols.build_ols_query(url)
    with requests_mock.mock() as m:
        m.get(ols_request_url, json=test_ols_data.TestGetTraitNamesData.orphanet_199318_ols_terms_json)
        assert ols.get_ontology_label_from_ols(url) == '15q13.3 microdeletion syndrome'


def test_is_current_and_in_efo():
    with requests_mock.mock() as m:
        url = f"{ols.OLS_BASE_URL}/api/ontologies/efo/terms/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_425"
        m.get(url,
              json=test_ols_data.TestIsCurrentAndInEfoData.orphanet_425_ols_efo_json)

        assert ols.is_current_and_in_ontology("http://www.orpha.net/ORDO/Orphanet_425") == True


def test_is_in_efo():
    with requests_mock.mock() as m:
        url = f"{ols.OLS_BASE_URL}/api/ontologies/efo/terms/http%253A%252F%252Fwww.orpha.net%252FORDO%252FOrphanet_425"
        m.get(url,
              json=test_ols_data.TestIsInEfoData.orphanet_425_ols_efo_json)

        assert ols.is_in_ontology("http://www.orpha.net/ORDO/Orphanet_425") == True
