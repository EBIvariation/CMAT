#!/usr/bin/env python3

import argparse

import pandas as pd


def export_table(input_filepath, done_filepath, comments_filepath):
    curation_table = pd.read_csv(input_filepath, skiprows=1, header=0)

    # Finished mappings
    done_rows = curation_table[curation_table['Status'] == 'DONE']
    done_rows = done_rows[['ClinVar label', 'URI of selected mapping', 'Label of selected mapping']]
    # Remove linebreaks
    done_rows['ClinVar label'] = done_rows['ClinVar label'].str.replace(r'[\n\r]+', '', regex=True)
    done_rows['URI of selected mapping'] = done_rows['URI of selected mapping'].str.replace(r'[\n\r]+', '', regex=True)
    done_rows['Label of selected mapping'] = done_rows['Label of selected mapping'].str.replace(r'[\n\r]+', '', regex=True)
    done_rows.to_csv(done_filepath, sep='\t', header=False, index=False)

    # Comments column
    comment_rows = curation_table[curation_table['Comment'].notna() & curation_table['Status'].notna()]
    comment_rows = comment_rows[['ClinVar label', 'Comment']].astype(str)
    # Remove double quotes as they just cause problems
    comment_rows['Comment'] = comment_rows['Comment'].str.replace('"', '')
    comment_rows.to_csv(comments_filepath, sep='\t', header=False, index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Export columns from CSV download of manual curation spreadsheet")
    parser.add_argument("-i", dest="input_filepath", required=True,
                        help="path to input csv file")
    parser.add_argument("-d", dest="done_filepath", required=True,
                        help="path to output file for terms that are done")
    parser.add_argument("-c", dest="comments_filepath", required=True,
                        help="path to output file for curator comments")
    args = parser.parse_args()
    export_table(args.input_filepath, args.done_filepath, args.comments_filepath)
