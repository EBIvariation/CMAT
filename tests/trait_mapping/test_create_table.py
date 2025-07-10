import pytest

from bin.trait_mapping.create_table_for_manual_curation import get_mapping_attributes_from_ols
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
