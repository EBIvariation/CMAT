from cmat.trait_mapping.utils import string_to_preferred_ontologies

def test_string_to_preferred_ontologies():
    assert string_to_preferred_ontologies('efo,hp,mondo', 'EFO') == ['mondo', 'hp']
    assert string_to_preferred_ontologies('mondo, hp', 'efo') == ['mondo', 'hp']
