#!/usr/bin/env python3
import argparse
import csv
import multiprocessing

from cmat.output_generation.clinvar_to_evidence_strings import load_ontology_mapping
from cmat.output_generation.evaluation.ols_utils import fetch_eval_data


def main(mapping_file, output_file):
    """Load mapping file, map identifiers to synonyms in OLS, and dump results to TSV."""
    mappings, target_ontology, _ = load_ontology_mapping(mapping_file)
    all_uris = [uri for v in mappings.values() for uri, _ in v]
    process_pool = multiprocessing.Pool(processes=24)
    annotated_traits = [
        process_pool.apply(fetch_eval_data, kwds={'uri': uri, 'include_neighbors': False, 'target_ontology': target_ontology})
        for uri in all_uris
    ]
    with open(output_file, 'w+') as f:
        csv.writer(f, delimiter="\t").writerows(annotated_traits)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to check if mappings are obsolete and find synonyms')
    parser.add_argument('--latest-mappings', required=True, help='Latest mappings file')
    parser.add_argument('--output-file', required=True, help='File to output dataframe')
    args = parser.parse_args()
    main(args.latest_mappings, args.output_file)
