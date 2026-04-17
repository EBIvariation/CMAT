import os.path

import cmat.trait_mapping.trait_names_parsing as trait_names_parsing


def test_trait_names_parsing():
    # Test file contains three records:
    # * one is processed normally
    # * one is excluded for having a non-specific trait name
    # * one is excluded due to being part of an excluded submission
    test_filename = os.path.join(os.path.dirname(__file__), 'resources/test_trait_parsing_input.xml.gz')
    parsed_traits = trait_names_parsing.parse_trait_names(test_filename)
    assert len(parsed_traits) == 1
    parsed_trait = parsed_traits[0]
    assert parsed_trait.name == 'leber congenital amaurosis 13'
    assert parsed_trait.is_associated_with_nt_expansion == False
    assert len(parsed_trait.xrefs) == 3
