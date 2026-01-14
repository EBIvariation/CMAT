#!/usr/bin/env python3

import argparse
import csv
import json
import os
import re

from cmat.clinvar_xml_io.ontology_uri import OntologyUri
from cmat.trait_mapping.ols import is_current_and_in_ontology


def get_ontology_id_regex(ot_schema_file):
    if not ot_schema_file:
        return '.*'
    with open(ot_schema_file, 'r') as f:
        schema = json.load(f)
        return schema['definitions']['diseaseFromSourceMappedId']['pattern']


def check_mappings(mappings_file, target_ontology, ot_schema_file):
    """
    Check mappings for obsolete terms and (optionally) conformity against regex in latest OT schema.
    Outputs a new mappings file and additional files of the mappings that have been removed.

    :param mappings_file: path to mappings file (tab-delimited, no header)
    :param target_ontology: ID of target ontology
    :param ot_schema_file: path to Open Targets JSON schema
    """
    with open(mappings_file, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        mappings = list(reader)
    ontology_id_regex = get_ontology_id_regex(ot_schema_file)
    updated_mappings = []
    obsolete_mappings = []
    nonmatching_mappings = []

    for trait_name, uri, label in mappings:
        if is_current_and_in_ontology(uri, target_ontology):
            if re.match(ontology_id_regex, OntologyUri.uri_to_curie(uri)):
                updated_mappings.append((label, uri))
            else:
                nonmatching_mappings.append((label, uri))
        else:
            obsolete_mappings.append((label, uri))

    # Output files
    filename = '.'.join(os.path.basename(mappings_file).split('.')[:-1])
    with open(f'{filename}_obsolete.tsv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        print(f'Removed {len(obsolete_mappings)} obsolete mappings')
        writer.writerows(sorted(obsolete_mappings))

    with open(f'{filename}_nonmatching.tsv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        print(f'Removed {len(nonmatching_mappings)} nonmatching mappings')
        writer.writerows(sorted(nonmatching_mappings))

    with open(f'{filename}_updated.tsv', 'w+') as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        print(f'{len(updated_mappings)} mappings remaining')
        writer.writerows(sorted(updated_mappings))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check latest mappings for obsolete terms and (optionally) conformity'
                                                 ' against latest OT schema')
    parser.add_argument('--mappings-file', required=True, help='File of latest ontology mappings to process')
    parser.add_argument('--target-ontology', required=False, default='EFO', help='Target ontology')
    parser.add_argument('--ot-schema', required=False, help='Open Targets schema JSON')
    args = parser.parse_args()
    check_mappings(args.mappings_file, args.target_ontology, args.ot_schema)
