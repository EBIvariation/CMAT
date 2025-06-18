import requests_mock

import cmat.trait_mapping.ols as ols
from cmat.trait_mapping.ols import OlsResult, MatchType, MappingSource, EXACT_SYNONYM_KEY
import resources.test_ols_data as test_ols_data


def test_get_label_and_synonyms_from_ols():
    url = "http://www.orpha.net/ORDO/Orphanet_199318"
    ols_request_url = ols.build_ols_query(url)
    with requests_mock.mock() as m:
        m.get(ols_request_url, json=test_ols_data.TestGetTraitNamesData.orphanet_199318_ols_terms_json)
        label, synonyms = ols.get_label_and_synonyms_from_ols(url)
        assert label == '15q13.3 microdeletion syndrome'
        assert sorted(synonyms) == ['Del(15)(q13.3)', 'Monosomy 15q13.3']


def test_is_current_and_in_efo():
    with requests_mock.mock() as m:
        url = f"{ols.OLS_BASE_URL}/ontologies/efo/classes/http%253A%252F%252Fwww.ebi.ac.uk%252Fefo%252FEFO_1000062"
        m.get(url,
              json=test_ols_data.TestIsInEfoData.efo_1000062_ols_efo_json)

        assert ols.is_current_and_in_ontology("http://www.ebi.ac.uk/efo/EFO_1000062") == True


def test_is_in_efo():
    with requests_mock.mock() as m:
        url = f"{ols.OLS_BASE_URL}/ontologies/efo/classes/http%253A%252F%252Fwww.ebi.ac.uk%252Fefo%252FEFO_1000062"
        m.get(url,
              json=test_ols_data.TestIsInEfoData.efo_1000062_ols_efo_json)

        assert ols.is_in_ontology("http://www.ebi.ac.uk/efo/EFO_1000062") == True


def test_get_fields_with_match():
    search_term = 'lactose malabsorption'
    query_fields = ['label', EXACT_SYNONYM_KEY]
    exact, contained, token = ols.get_fields_with_match(search_term, query_fields,
                                                        test_ols_data.TestIsInEfoData.efo_1000062_ols_efo_json)
    assert exact == []
    assert contained == [EXACT_SYNONYM_KEY]
    assert token == ['label']


def test_ols_result():
    ols_result_1 = OlsResult(
        uri='http://purl.obolibrary.org/obo/HP_0006740',
        label='Transitional cell carcinoma of the bladder',
        full_exact_match=[],
        contained_match=['label'],
        token_match=['synonym'],
        in_target_ontology=False,
        in_preferred_ontology=True,
        is_current=False
    )
    ols_result_2 = OlsResult(
        uri='http://purl.obolibrary.org/obo/MONDO_0004986',
        label='urinary bladder carcinoma',
        full_exact_match=['synonym'],
        contained_match=[],
        token_match=['synonym'],
        in_target_ontology=False,
        in_preferred_ontology=True,
        is_current=False
    )
    ols_result_3 = OlsResult(
        uri='http://purl.obolibrary.org/obo/EFO_123',
        label='urinary bladder carcinoma',
        full_exact_match=['synonym'],
        contained_match=[],
        token_match=['synonym'],
        in_target_ontology=True,
        in_preferred_ontology=True,
        is_current=True
    )
    assert ols_result_1.get_match_type() == MatchType.CONTAINED_MATCH_LABEL
    assert ols_result_1.get_mapping_source() == MappingSource.PREFERRED_NOT_TARGET
    assert ols_result_2.get_match_type() == MatchType.EXACT_MATCH_SYNONYM
    assert ols_result_2.get_mapping_source() == MappingSource.PREFERRED_NOT_TARGET
    assert ols_result_3.get_match_type() == MatchType.EXACT_MATCH_SYNONYM
    assert ols_result_3.get_mapping_source() == MappingSource.TARGET_CURRENT

    # Full exact matches are preferred to contained matches, regardless of which field is matched
    assert ols_result_2 > ols_result_1
    # All else being equal, mappings in the target ontology are preferred
    assert ols_result_3 > ols_result_2


def test_mapping_source_to_string():
    assert MappingSource.TARGET_OBSOLETE.to_string('efo', ['mondo','hp']) == 'EFO_OBSOLETE'
    assert MappingSource.PREFERRED_NOT_TARGET.to_string('efo', ['mondo','hp']) == 'MONDO_HP_NOT_EFO'
