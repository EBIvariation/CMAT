from unittest.mock import patch

from bin.trait_mapping.create_latest_mappings import create_latest_mappings


def test_create_latest_mappings():
    previous_mappings = {
        # Obsolete mapping
        'A': [('http://www.ebi.ac.uk/efo/EFO_obsolete', 'obsolete'),
              ('http://www.ebi.ac.uk/efo/EFO_A', 'A')],
        # Duplicate mappings
        'B': [('http://www.ebi.ac.uk/efo/EFO_B', 'B'),
              ('http://www.ebi.ac.uk/efo/EFO_B', 'B')],
        'C': [('http://www.ebi.ac.uk/efo/EFO_unused', 'unused')],
        'D': [('http://www.ebi.ac.uk/efo/EFO_unused', 'unused')]
    }
    automated_mappings = {
        # Overrides previous mappings
        'C': [('http://www.ebi.ac.uk/efo/EFO_C', 'C')],
        'D': [('http://www.ebi.ac.uk/efo/EFO_automated', 'automated')]
    }
    curated_mappings = {
        # Overrides previous and automated mappings
        'D': [('http://www.ebi.ac.uk/efo/EFO_D', 'D')],
        'E': [('http://www.ebi.ac.uk/efo/EFO_E', 'E')]
    }

    with patch('bin.trait_mapping.create_latest_mappings.is_current_and_in_ontology') as m_is_current:
        m_is_current.side_effect = lambda uri, ont: False if 'obsolete' in uri else True
        current_mappings, obsolete_mappings = create_latest_mappings(automated_mappings, curated_mappings,
                                                                     previous_mappings, 'EFO')
        assert obsolete_mappings == [('A', 'http://www.ebi.ac.uk/efo/EFO_obsolete', 'obsolete')]
        assert current_mappings == [(ch, f'http://www.ebi.ac.uk/efo/EFO_{ch}', ch) for ch in 'ABCDE']


def test_create_latest_mappings_multiples():
    previous_mappings = {
        'A': [('http://www.ebi.ac.uk/efo/EFO_A1', 'A1'),
              ('http://www.ebi.ac.uk/efo/EFO_A2', 'A2')],
        'B': [('http://www.ebi.ac.uk/efo/EFO_B1', 'B1')],
        'C': [('http://www.ebi.ac.uk/efo/EFO_C1', 'C1')]
    }
    automated_mappings = {}
    curated_mappings = {
        'A': [('http://www.ebi.ac.uk/efo/EFO_A3', 'A3')],
        'B': [('http://www.ebi.ac.uk/efo/EFO_B2', 'B2'),
              ('http://www.ebi.ac.uk/efo/EFO_B3', 'B3')]
    }

    with patch('bin.trait_mapping.create_latest_mappings.is_current_and_in_ontology') as m_is_current:
        m_is_current.return_value = True
        current_mappings, obsolete_mappings = create_latest_mappings(automated_mappings, curated_mappings,
                                                                     previous_mappings, 'EFO')
        assert obsolete_mappings == []
        assert current_mappings == [
            ('A', 'http://www.ebi.ac.uk/efo/EFO_A3', 'A3'),
            ('B', 'http://www.ebi.ac.uk/efo/EFO_B2', 'B2'),
            ('B', 'http://www.ebi.ac.uk/efo/EFO_B3', 'B3'),
            ('C', 'http://www.ebi.ac.uk/efo/EFO_C1', 'C1')
        ]
