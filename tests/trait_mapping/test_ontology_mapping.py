import pytest

from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingContext, MappingProvenance, MatchType, \
    MappingSource


@pytest.mark.integration
def test_to_mapping_string():
    mapping_context = MappingContext('aprt deficiency, japanese type', 'efo', ['mondo', 'hp'])
    mapping = OntologyMapping(mapping_context, 'http://www.orpha.net/ORDO/Orphanet_976', MappingProvenance.PREVIOUS)
    assert str(mapping) == 'http://www.orpha.net/ORDO/Orphanet_976|Adenine phosphoribosyltransferase deficiency|PREVIOUS|NO_MATCH|EFO_OBSOLETE'


@pytest.mark.integration
def test_get_mapping_attributes():
    mapping_context = MappingContext('11p partial monosomy syndrome', 'efo', ['mondo', 'hp'])
    mapping = OntologyMapping(mapping_context, 'http://purl.obolibrary.org/obo/MONDO_0008681', MappingProvenance.PREVIOUS)
    assert mapping.label == 'WAGR syndrome'
    assert mapping.get_match_type() == MatchType.EXACT_MATCH_SYNONYM
    assert mapping.get_mapping_source() == MappingSource.TARGET_CURRENT
