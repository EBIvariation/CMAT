import os.path

import cmat.trait_mapping.trait_names_parsing as trait_names_parsing


def test_trait_names_parsing():
    # Test file contains three records:
    # * one is processed normally
    # * one is excluded for having a non-specific trait name
    # * one is excluded due to being part of an excluded submission
    test_filename = os.path.join(os.path.dirname(__file__), 'resources/test_trait_parsing_input.xml.gz')
    trait_names = [trait.name for trait in trait_names_parsing.parse_trait_names(test_filename)]
    assert trait_names == ['leber congenital amaurosis 13']
