from copy import deepcopy
from random import shuffle

import pytest

from cmat.trait_mapping.ols import EXACT_SYNONYM_KEY
from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingContext, MappingProvenance, MatchType, \
    MappingSource, ClinVarXrefMapping


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


def sort_and_assert_ranking(expected_mappings):
    test_mappings = deepcopy(expected_mappings)
    while test_mappings == expected_mappings:
        shuffle(test_mappings)

    test_mappings.sort()
    assert test_mappings == expected_mappings


def test_ranking_same_provenance():
    # Test ranking among mappings with the same provenance
    mapping_context = MappingContext('something', 'efo', ['mondo', 'hp'])
    # Expected order of mappings
    expected_mappings = [
        # OLS exact label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, ['label'], [], []),
        # OLS exact label in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', False, True, False, ['label'], [], []),
        # OLS exact synonym in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', False, True, False, [EXACT_SYNONYM_KEY], [], []),
        # OLS contained match label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', False, True, False, [], ['label'], []),
        # OLS token match label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, [], [], ['label']),
        # OLS exact label in neither
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', False, False, False, ['label'], [], []),
    ]
    sort_and_assert_ranking(expected_mappings)


def test_ranking_same_match_type():
    # Test ranking among mappings with the same match type
    mapping_context = MappingContext('something', 'efo', ['mondo', 'hp'])
    # Expected order of mappings
    expected_mappings = [
        # Previous in target (current)
        OntologyMapping(mapping_context, 'uri', MappingProvenance.PREVIOUS, 'label', True, False, True, [], [], ['label']),
        # OLS in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, [], [],['label']),
        # Previous in target (obsolete)
        OntologyMapping(mapping_context, 'uri', MappingProvenance.PREVIOUS, 'label', True, False, False, [], [],['label']),
        # OxO in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OXO, 'label', False, True, False, [], [],['label']),
        # ClinVar in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.CLINVAR_XREF, 'label', False, True, False, [], [], ['label']),
        # ClinVar in other
        OntologyMapping(mapping_context, 'uri', MappingProvenance.CLINVAR_XREF, 'label', False, False, False, [], [], ['label']),
    ]
    sort_and_assert_ranking(expected_mappings)


def test_ranking_same_mapping_source():
    # Test ranking among mappings with the same mapping source
    mapping_context = MappingContext('something', 'efo', ['mondo', 'hp'])
    # Expected order of mappings
    expected_mappings = [
        # Previous, any match type
        OntologyMapping(mapping_context, 'uri', MappingProvenance.PREVIOUS, 'label', True, False, True, [], [], [EXACT_SYNONYM_KEY]),
        # OLS, exact label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, ['label'], [],[]),
        # Zooma, exact label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.ZOOMA, 'label', True, False, True, ['label'], [], []),
        # OxO, exact label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OXO, 'label', True, False, True, ['label'], [], []),
        # ClinVar, exact label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.CLINVAR_XREF, 'label', True, False, True, ['label'], [], []),
        # OLS, exact synonym
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, [EXACT_SYNONYM_KEY], [], []),
        # OLS, contained label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, [],['label'], []),
        # OLS, token label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS, 'label', True, False, True, [], [], ['label']),
    ]
    sort_and_assert_ranking(expected_mappings)
