#!/usr/bin/env python3
import argparse
from copy import deepcopy
from datetime import datetime

from cmat.output_generation.clinvar_to_evidence_strings import load_ontology_mapping
from cmat.trait_mapping.ols import is_current_and_in_ontology


OUTPUT_FILE_NAME = 'trait_names_to_ontology_mappings.tsv'
OBSOLETE_FILE_NAME = 'obsolete_mappings.tsv'


def create_latest_mappings(automated_mappings, curated_mappings, previous_mappings, target_ontology):
    # Combine automated, curated and previous mappings
    latest_mappings = deepcopy(previous_mappings)
    latest_mappings.update(automated_mappings)
    latest_mappings.update(curated_mappings)

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
    return current_rows, obsolete_rows


def output_files(current_mappings, obsolete_mappings, target_ontology):
    with open(OUTPUT_FILE_NAME, 'w') as out_file:
        out_file.write(f'#generated-date={datetime.today().strftime("%Y-%m-%d")}\n')
        out_file.write(f'#ontology=${target_ontology}\n')
        out_file.write('#clinvar_trait_name\turi\tlabel\n')
        for trait_name, uri, label in current_mappings:
            out_file.write(f'{trait_name}\t{uri}\t{label}\n')

    with open(OBSOLETE_FILE_NAME, 'w') as obs_file:
        for trait_name, uri, label in obsolete_mappings:
            obs_file.write(f'{trait_name}\t{uri}\t{label}\n')


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

    current_mappings, obsolete_mappings = create_latest_mappings(automated_mappings, curated_mappings,
                                                                 previous_mappings, target_ontology)
    output_files(current_mappings, obsolete_mappings, target_ontology)
