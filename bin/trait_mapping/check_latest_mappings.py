#!/usr/bin/env python3

import argparse
import csv
import json
import os
import re


def get_ontology_id_regex(ot_schema_file):
    if not ot_schema_file:
        return '.*'
    with open(ot_schema_file, 'r') as f:
        schema = json.load(f)
        return schema['definitions']['diseaseFromSourceMappedId']['pattern']


def check_mappings(mappings_file, ot_schema_file):
    """
    Check mappings for conformity against regex in latest OT schema.
    Outputs a new mappings file and a file of the mappings that have been removed.

    :param mappings_file: path to mappings file (tab-delimited, no header)
    :param ot_schema_file: path to Open Targets JSON schema
    """
    with open(mappings_file, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        mappings = list(reader)
    ontology_id_regex = get_ontology_id_regex(ot_schema_file)
    updated_mappings = set()
    nonmatching_mappings = set()

    for trait_name, uri, label in mappings:
        if re.match(ontology_id_regex, uri.split('/')[-1]):
            updated_mappings.add((label, uri))
        else:
            nonmatching_mappings.add((label, uri))

    # Output files
    filename = '.'.join(os.path.basename(mappings_file).split('.')[:-1])
    with open(f'{filename}_nonmatching.tsv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        print(f'Removed {len(nonmatching_mappings)} nonmatching mappings')
        writer.writerows(sorted(list(nonmatching_mappings)))

    with open(f'{filename}_updated.tsv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        print(f'{len(updated_mappings)} mappings remaining')
        writer.writerows(sorted(list(updated_mappings)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check latest mappings for obsolete terms and (optionally) conformity'
                                                 ' against latest OT schema')
    parser.add_argument('--mappings-file', required=True, help='File of latest ontology mappings to process')
    parser.add_argument('--ot-schema', required=True, help='Open Targets schema JSON')
    args = parser.parse_args()
    check_mappings(args.mappings_file, args.ot_schema)
