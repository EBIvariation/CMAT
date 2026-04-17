from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingContext, MappingProvenance


def test_to_mapping_string():
    mapping_context = MappingContext('aprt deficiency, japanese type', 'efo', ['mondo', 'hp'])
    mapping = OntologyMapping(mapping_context, 'http://www.orpha.net/ORDO/Orphanet_976', MappingProvenance.PREVIOUS, )
    assert str(mapping) == 'http://www.orpha.net/ORDO/Orphanet_976|Adenine phosphoribosyltransferase deficiency|PREVIOUS|NO_MATCH|EFO_OBSOLETE'


# TODO additional tests
