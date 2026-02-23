#!/usr/bin/env python3

import argparse

import pandas as pd


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--traits-for-curation',
        help='Table with traits for which the pipeline failed to make a confident prediction')
    parser.add_argument(
        '-c', '--previous-comments',
        help='Table with last round of curator comments. TSV with columns: ClinVar trait name; comments')
    parser.add_argument(
        '-o', '--output',
        help='Output TSV to be loaded in Google Sheets for manual curation')
    args = parser.parse_args()

    # Load previous curator comments: ClinVar trait name to comment string
    try:
        previous_comments = pd.read_csv(args.previous_comments, sep='\t', header=None)
        previous_comments = dict(zip(previous_comments[0], previous_comments[1]))
    except (FileNotFoundError, pd.errors.EmptyDataError):
        previous_comments = {}

    # Process all mappings which require manual curation
    rows = []
    for line in open(args.traits_for_curation):
        fields = line.split('\t')
        fields[-1] = fields[-1].rstrip()  # To avoid stripping the entire field if it's empty
        trait_name, trait_freq, notes = fields[:3]
        # Add previous curator comment if present
        if trait_name in previous_comments:
            notes = f'"{notes}\n{previous_comments[trait_name]}"'
        rows.append([trait_name, trait_freq, notes] + fields[3:])

    rows.sort(key=lambda x: (x[2], int(x[1])), reverse=True)
    with open(args.output, 'w') as outfile:
        for row in rows:
            out_line = '\t'.join(row) + '\n'
            outfile.write(out_line)
