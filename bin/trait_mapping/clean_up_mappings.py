#!/usr/bin/env python3

import argparse
import csv
import os.path
from collections import defaultdict

from cmat.trait_mapping.ols import is_current_and_in_ontology

from cmat.output_generation.clinvar_to_evidence_strings import load_ontology_mapping


def flatten_dict(d):
    # key -> [(x1, y1), (x2, y2)] ==> [(key, x1, y1), (key, x2, y2)]
    result = []
    for key in d:
        for (x, y) in d[key]:
            result.append((key, x, y))
    return result


def main(mappings_file):
    mappings, target_ontology = load_ontology_mapping(mappings_file)

    obsolete_mappings = defaultdict(list)
    multiple_mappings = {}
    current_mappings = {}

    for trait_name, mapping_list in mappings.items():
        keep_mappings = []
        # Remove obsolete mappings
        for uri, label in mapping_list:
            if not is_current_and_in_ontology(uri, target_ontology):
                obsolete_mappings[trait_name].append((uri, label))
            else:
                keep_mappings.append((uri, label))
        # Remove multiple mappings
        if len(keep_mappings) > 1:
            multiple_mappings[trait_name] = keep_mappings
        else:
            current_mappings[trait_name] = keep_mappings

    # Output files
    filename = '.'.join(os.path.basename(mappings_file).split('.')[:-1])
    with open(f'{filename}_obsolete.csv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        obsolete_rows = flatten_dict(obsolete_mappings)
        print(f'Removed {len(obsolete_rows)} obsolete mappings')
        writer.writerows(obsolete_rows)

    with open(f'{filename}_multiple.csv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        multiple_rows = flatten_dict(multiple_mappings)
        print(f'Removed {len(multiple_rows)} multiple mappings')
        writer.writerows(multiple_rows)

    with open(f'{filename}_current.csv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        current_rows = flatten_dict(current_mappings)
        print(f'{len(current_rows)} mappings remaining')
        writer.writerows(current_rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Clean up obsolete and multiple mappings')
    parser.add_argument('--mappings-file', required=True, help='File of latest ontology mappings to process')
    args = parser.parse_args()
    main(args.mappings_file)
