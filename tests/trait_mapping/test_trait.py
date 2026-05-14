import cmat.trait_mapping.trait as trait
from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingContext, MappingProvenance, MappingSource


def test_is_finished_true():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)
    test_trait.finished_mapping_set.add(trait.OntologyEntry('http://www.orpha.net/ORDO/Orphanet_976',
                                                            'Adenine phosphoribosyltransferase deficiency'))
    assert test_trait.is_finished


def test_is_finished_false():
    test_trait = trait.Trait('aprt deficiency, japanese type', '99999', 1)
    assert not test_trait.is_finished


def test_assess_if_finished():
    test_trait = trait.Trait('Hereditary factor VIII deficiency disease', '99999', 11)
    mapping_context = MappingContext(test_trait.name, 'efo', ['mondo', 'hp'])
    mappings = [
        OntologyMapping(
            mapping_context=mapping_context,
            uri='http://snomed.info/id/28293008',
            provenance=MappingProvenance.CLINVAR_XREF,
            label='Hereditary factor VIII deficiency disease',
            exact_match=['label'],
            contained_match=[],
            token_match=[],
            in_target_ontology=False,
            in_preferred_ontology=False,
            is_current=False
        ),
        # MONDO_0010602 in EFO via ClinVar
        OntologyMapping(
            mapping_context=mapping_context,
            uri='http://purl.obolibrary.org/obo/MONDO_0010602',
            provenance=MappingProvenance.CLINVAR_XREF,
            label='hemophilia A',
            exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
            contained_match=[],
            token_match=['label'],
            in_target_ontology=True,
            in_preferred_ontology=False,
            is_current=True
        ),
        # MONDO_0010602 in EFO via OLS
        OntologyMapping(
            mapping_context=mapping_context,
            uri='http://purl.obolibrary.org/obo/MONDO_0010602',
            provenance=MappingProvenance.OLS,
            label='hemophilia A',
            exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
            contained_match=[],
            token_match=['label'],
            in_target_ontology=True,
            in_preferred_ontology=False,
            is_current=True
        ),
        # MONDO_0010602 in Mondo via OLS
        OntologyMapping(
            mapping_context=mapping_context,
            uri='http://purl.obolibrary.org/obo/MONDO_0010602',
            provenance=MappingProvenance.OLS,
            label='hemophilia A',
            exact_match=['http://www.geneontology.org/formats/oboInOwl#hasExactSynonym'],
            contained_match=[],
            token_match=['label'],
            in_target_ontology=False,
            in_preferred_ontology=True,
            is_current=False
        )
    ]
    test_trait.candidate_mappings = mappings

    test_trait.assess_if_finished()

    # Only 1 version of MONDO_0010602 is kept (in EFO via OLS)
    assert len(test_trait.candidate_mappings) == 2
    assert test_trait.candidate_mappings[0].uri == 'http://purl.obolibrary.org/obo/MONDO_0010602'
    assert test_trait.candidate_mappings[0].provenance == MappingProvenance.OLS
    assert test_trait.candidate_mappings[0].get_mapping_source() == MappingSource.TARGET_CURRENT

    assert test_trait.candidate_mappings[1].uri == 'http://snomed.info/id/28293008'
    assert test_trait.candidate_mappings[1].provenance == MappingProvenance.CLINVAR_XREF
    assert test_trait.candidate_mappings[1].get_mapping_source() == MappingSource.NOT_PREFERRED_TARGET
