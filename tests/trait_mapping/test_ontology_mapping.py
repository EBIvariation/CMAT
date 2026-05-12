from copy import deepcopy
from random import shuffle

import pytest

from cmat.trait_mapping.ols import EXACT_SYNONYM_KEY
from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingContext, MappingProvenance, MatchType, \
    MappingSource, ClinVarXrefMapping
from cmat.trait_mapping.oxo import OxoMapping
from cmat.trait_mapping.zooma import ZoomaMapping, ZoomaConfidence


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


@pytest.mark.integration
def test_non_ontology_mapping():
    mapping_context = MappingContext('11p partial monosomy syndrome', 'efo', ['mondo', 'hp'])
    mapping = ClinVarXrefMapping(mapping_context, 'http://identifiers.org/medgen/C0206115')
    assert mapping.label == ''
    assert mapping.get_match_type() == MatchType.NO_MATCH
    assert mapping.get_mapping_source() == MappingSource.NOT_PREFERRED_TARGET


def test_ontology_mapping_ranking_same_provenance():
    mapping_context = MappingContext('something', 'efo', ['mondo', 'hp'])
    expected_mappings = [
        # OLS exact label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, None, True, False, True, ['label'], [], []),
        # OLS exact label in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, None, False, True, False, ['label'], [], []),
        # OLS exact synonym in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, None, False, True, False, [EXACT_SYNONYM_KEY], [], []),
        # OLS token match label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, None, True, False, True, [], [], ['label']),
        # OLS contained match label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, None, False, True, False, [], ['label'], []),
        # OLS exact label in neither
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, None, False, False, False, ['label'], [], []),
    ]
    test_mappings = deepcopy(expected_mappings)
    while test_mappings == expected_mappings:
        shuffle(test_mappings)

    test_mappings.sort()
    assert test_mappings == expected_mappings
