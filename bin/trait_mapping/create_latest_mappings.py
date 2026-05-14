#!/usr/bin/env python3
import argparse
from copy import deepcopy
from datetime import datetime

import yaml

from cmat.trait_mapping.ols import is_current_and_in_ontology
from cmat.trait_mapping.utils import load_ontology_mapping

OUTPUT_FILE_NAME = 'trait_names_to_ontology_mappings.tsv'
OBSOLETE_FILE_NAME = 'obsolete_mappings.tsv'
COUNTS_FILE_NAME = 'trait_counts.yml'


def create_latest_mappings(automated_mappings, curated_mappings, previous_mappings, target_ontology):
    # Combine automated, curated and previous mappings
    # Also count how many traits have their mappings updated or added by automation or curation (before filtering out
    # duplicates or obsolete terms)
    counts = {
        'n_previous_unchanged': 0,
        'n_automated_updated': 0,
        'n_automated_new': 0,
        'n_curated_updated': 0,
        'n_curated_new': 0
    }
    latest_mappings = deepcopy(previous_mappings)
    counts['n_previous_unchanged'] = len(previous_mappings)
    for trait_name in automated_mappings:
        if trait_name in latest_mappings:
            if latest_mappings[trait_name] != automated_mappings[trait_name]:
                latest_mappings[trait_name] = automated_mappings[trait_name]
                counts['n_automated_updated'] += 1
                counts['n_previous_unchanged'] -= 1
        else:
            latest_mappings[trait_name] = automated_mappings[trait_name]
            counts['n_automated_new'] += 1
    for trait_name in curated_mappings:
        if trait_name in latest_mappings:
            if latest_mappings[trait_name] != curated_mappings[trait_name]:
                latest_mappings[trait_name] = curated_mappings[trait_name]
                counts['n_curated_updated'] += 1
                if trait_name in automated_mappings and previous_mappings[trait_name] != automated_mappings[trait_name]:
                    counts['n_automated_updated'] -= 1
                else:
                    counts['n_previous_unchanged'] -= 1
        else:
            latest_mappings[trait_name] = curated_mappings[trait_name]
            counts['n_curated_new'] += 1

    assert sum(counts.values()) == len(latest_mappings), 'Trait counts not consistent'

    # Ensure no duplicate rows or obsolete mappings
    current_rows = set()
    obsolete_rows = set()
    for trait_name, mappings in latest_mappings.items():
        for uri, label in mappings:
            if is_current_and_in_ontology(uri, target_ontology):
                current_rows.add((trait_name, uri, label))
            else:
                obsolete_rows.add((trait_name, uri, label))

    current_rows = sorted(list(current_rows))
    obsolete_rows = sorted(list(obsolete_rows))
    return current_rows, obsolete_rows, counts


def output_and_report(current_mappings, obsolete_mappings, target_ontology, counts):
    with open(OUTPUT_FILE_NAME, 'w') as out_file:
        out_file.write(f'#generated-date={datetime.today().strftime("%Y-%m-%d")}\n')
        out_file.write(f'#ontology={target_ontology}\n')
        out_file.write('#clinvar_trait_name\turi\tlabel\n')
        for trait_name, uri, label in current_mappings:
            out_file.write(f'{trait_name}\t{uri}\t{label}\n')

    with open(OBSOLETE_FILE_NAME, 'w') as obs_file:
        for trait_name, uri, label in obsolete_mappings:
            obs_file.write(f'{trait_name}\t{uri}\t{label}\n')

    print(f'Number of traits with mappings:')
    print(f'\tUnchanged from previous: {counts["n_previous_unchanged"]}')
    print(f'\tUpdated by automation: {counts["n_automated_updated"]}')
    print(f'\tAdded by automation: {counts["n_automated_new"]}')
    print(f'\tUpdated by curation: {counts["n_curated_updated"]}')
    print(f'\tAdded by curation: {counts["n_curated_new"]}')
    with open(COUNTS_FILE_NAME, 'w') as counts_file:
        yaml.dump(counts, counts_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create latest mapping file by combining automated, curated, and previous mappings')
    parser.add_argument('--automated', required=True, help='Path to automated mappings TSV file')
    parser.add_argument('--curated', required=True, help='Path to curated mappings TSV file')
    parser.add_argument('--previous', required=True, help='Path to previous mappings TSV file')
    args = parser.parse_args()

    automated_mappings, _, _ = load_ontology_mapping(args.automated)
    curated_mappings, _, _ = load_ontology_mapping(args.curated)
    previous_mappings, target_ontology, _ = load_ontology_mapping(args.previous)

    current_mappings, obsolete_mappings, counts = create_latest_mappings(automated_mappings, curated_mappings,
                                                                         previous_mappings, target_ontology)
    output_and_report(current_mappings, obsolete_mappings, target_ontology, counts)
