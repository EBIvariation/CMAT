#!/usr/bin/env python3
import argparse
from datetime import datetime

from cmat.output_generation.clinvar_to_evidence_strings import load_ontology_mapping
from cmat.trait_mapping.ols import is_current_and_in_ontology


OUTPUT_FILE_NAME = 'trait_names_to_ontology_mappings.tsv'
OBSOLETE_FILE_NAME = 'obsolete_mappings.tsv'


def create_latest_mappings(automated_file, curated_file, previous_file):
    # Combine automated, curated and previous mappings
    automated_mappings, _, _ = load_ontology_mapping(automated_file)
    curated_mappings, _, _ = load_ontology_mapping(curated_file)
    latest_mappings, target_ontology, _ = load_ontology_mapping(previous_file)
    latest_mappings.update(automated_mappings)
    latest_mappings.update(curated_mappings)

    # Check for obsolete mappings and write output
    with open(OUTPUT_FILE_NAME, 'w') as out_file, open(OBSOLETE_FILE_NAME, 'w') as obs_file:
        out_file.write(f'#generated-date={datetime.today().strftime("%Y-%m-%d")}\n')
        out_file.write(f'#ontology=${target_ontology}\n')
        out_file.write(f'#clinvar_trait_name\turi\tlabel\n')

        for trait_name, mappings in latest_mappings.items():
            for uri, label in mappings:
                s = f'{trait_name}\t{uri}\t{label}\n'
                if is_current_and_in_ontology(uri, target_ontology):
                    out_file.write(s)
                else:
                    obs_file.write(s)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Export columns from CSV download of manual curation spreadsheet")
    parser.add_argument('--automated', required=True, help='Path to automated mappings TSV file')
    parser.add_argument('--curated', required=True, help='Path to curated mappings TSV file')
    parser.add_argument('--previous', required=True, help='Path to previous mappings TSV file')
    args = parser.parse_args()

    create_latest_mappings(args.automated, args.curated, args.previous)
