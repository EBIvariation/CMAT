import pytest

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


def test_ontology_mapping():
    mapping_context = MappingContext('something', 'efo', ['mondo', 'hp'])
    mappings = [
        # Previous mapping
        OntologyMapping(mapping_context, 'uri', MappingProvenance.PREVIOUS),
        # Obsolete previous mapping
        OntologyMapping(mapping_context, 'uri', MappingProvenance.PREVIOUS),
        # Zooma high confidence
        ZoomaMapping(mapping_context, 'uri', ZoomaConfidence.HIGH, ''),
        # Zooma lower confidence
        ZoomaMapping(mapping_context, 'uri', ZoomaConfidence.GOOD, ''),
        # Oxo distance 1
        OxoMapping(mapping_context, 'uri', '', 1, ''),
        # OLS exact label in target
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS),
        # OLS exact label in preferred
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS),
        # OLS exact label in neither
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS),
        # OLS exact synonym
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS),
        # OLS contained label
        OntologyMapping(mapping_context, 'uri', MappingProvenance.OLS),
        # ClinVar Xref in preferred
        ClinVarXrefMapping(mapping_context, 'uri'),
        # ClinVar Xref in neither
        ClinVarXrefMapping(mapping_context, 'uri'),
    ]
