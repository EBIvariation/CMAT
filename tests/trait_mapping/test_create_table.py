import pytest

from bin.trait_mapping.create_table_for_manual_curation import get_mapping_attributes_from_ols, find_replacement_mapping
from cmat.trait_mapping.ols import MappingSource, MatchType


@pytest.mark.integration
def test_get_mapping_attributes():
    label, match_type, mapping_source = get_mapping_attributes_from_ols(
        trait_name='11p partial monosomy syndrome',
        uri='http://purl.obolibrary.org/obo/MONDO_0008681',
        target_ontology='EFO',
        preferred_ontologies=['mondo', 'hp']
    )
    assert label == 'WAGR syndrome'
    assert match_type == MatchType.EXACT_MATCH_SYNONYM
    assert mapping_source == MappingSource.TARGET_CURRENT


@pytest.mark.integration
def test_find_replacement_mapping():
    trait_name = 'genetic transient congenital hypothyroidism'
    target_ontology = 'efo'
    preferred_ontologies = ['mondo', 'hp']

    # Current in EFO - no replacement term
    assert find_replacement_mapping(trait_name, 'http://purl.obolibrary.org/obo/MONDO_0011792', target_ontology, preferred_ontologies) == ''

    # Deprecated in EFO with current replacement term
    assert find_replacement_mapping(trait_name, 'http://www.ebi.ac.uk/efo/EFO_0000665', target_ontology, preferred_ontologies) == 'http://purl.obolibrary.org/obo/MONDO_0037939|porphyria|TOKEN_MATCH_SYNONYM|EFO_CURRENT'

    # Deprecated in EFO but replacement is also deprecated.
    # The replacement itself has a replacement in Mondo but not in EFO, so no replacement is found
    assert find_replacement_mapping(trait_name, 'http://www.orpha.net/ORDO/Orphanet_226316', target_ontology, preferred_ontologies) == ''
