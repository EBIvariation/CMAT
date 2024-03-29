import os.path

import cmat.trait_mapping.trait_names_parsing as trait_names_parsing


def test_trait_names_parsing():
    # Test file contains two records: one with a Pathogenic variant another with a Benign one. Trait names
    # from *both* records must be parsed and returned.
    test_filename = os.path.join(os.path.dirname(__file__),
                                 '../output_generation/resources/test_clinvar_record.xml.gz')
    trait_names = [trait.name for trait in trait_names_parsing.parse_trait_names(test_filename)]
    assert trait_names == ['leber congenital amaurosis 13']
