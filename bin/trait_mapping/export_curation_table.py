#!/usr/bin/env python3

import argparse

import pandas as pd


STATUS_HEADER = 'Status'
CLINVAR_LABEL_HEADER = 'ClinVar label'
MAPPING_URI_HEADER = 'URI of selected mapping'
MAPPING_LABEL_HEADER = 'Label of selected mapping'
COMMENT_HEADER = 'Comment'


def export_table(input_filepath, batch_date, done_filepath, skipped_filepath, comments_filepath,
                 import_filepath):
    curation_table = pd.read_csv(input_filepath, skiprows=1, header=0)

    # Remove linebreaks
    curation_table[CLINVAR_LABEL_HEADER] = curation_table[CLINVAR_LABEL_HEADER].str.replace(r'[\n\r]+', '', regex=True)
    curation_table[MAPPING_URI_HEADER] = curation_table[MAPPING_URI_HEADER].str.replace(r'[\n\r]+', '', regex=True)
    curation_table[MAPPING_LABEL_HEADER] = curation_table[MAPPING_LABEL_HEADER].str.replace(r'[\n\r]+', '', regex=True)

    # Finished mappings
    done_rows = curation_table[curation_table[STATUS_HEADER] == 'DONE']
    done_rows = done_rows[[CLINVAR_LABEL_HEADER, MAPPING_URI_HEADER, MAPPING_LABEL_HEADER]]
    done_rows.to_csv(done_filepath, sep='\t', header=False, index=False)

    # Import mappings
    import_rows = curation_table[curation_table[STATUS_HEADER] == 'DONE']
    import_rows = import_rows[[MAPPING_LABEL_HEADER, MAPPING_URI_HEADER]]
    import_rows[MAPPING_URI_HEADER] = import_rows[MAPPING_URI_HEADER].str.rsplit('/', n=1).str[-1]
    with open(import_filepath, 'w') as import_file:
        import_file.write('| Label | ID |\n')
        import_file.write('| --- | --- |\n')
        for _, row in import_rows.iterrows():
            label = str(row[MAPPING_LABEL_HEADER]).replace('|', '\\|')
            identifier = str(row[MAPPING_URI_HEADER]).replace('|', '\\|')
            import_file.write(f'| {label} | {identifier} |\n')

    # Skipped terms
    skip_rows = curation_table[curation_table[STATUS_HEADER] == 'SKIP']
    skip_rows['Date'] = batch_date
    skip_rows = skip_rows[[CLINVAR_LABEL_HEADER, 'Date']]
    skip_rows.to_csv(skipped_filepath, sep='\t', header=False, index=False)

    # Comments column
    comment_rows = curation_table[curation_table[COMMENT_HEADER].notna() & curation_table[STATUS_HEADER].notna()]
    comment_rows = comment_rows[[CLINVAR_LABEL_HEADER, COMMENT_HEADER]].astype(str)
    # Remove double quotes as they just cause problems
    comment_rows[COMMENT_HEADER] = comment_rows[COMMENT_HEADER].str.replace('"', '')
    comment_rows.to_csv(comments_filepath, sep='\t', header=False, index=False)


def export_new_terms(new_input_filepath, new_output_filepath):
    new_terms_table = pd.read_csv(new_input_filepath, header=0)
    with open(new_output_filepath, 'w') as new_terms_file:
        headers = [column for column in new_terms_table.columns]
        new_terms_file.write(f"| {' | '.join(headers)} |\n")
        new_terms_file.write(f"| {' | '.join('---' for _ in headers)} |\n")
        for _, row in new_terms_table.iterrows():
            values = [str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
                      for value in row.fillna('')]
            new_terms_file.write(f"| {' | '.join(values)} |\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Export columns from CSV download of manual curation spreadsheet")
    parser.add_argument("-i", dest="input_filepath", required=True,
                        help="path to input csv file")
    parser.add_argument("-e", dest="new_input_filepath", required=False,
                        help="path to input new terms csv file")
    parser.add_argument("-b", dest="batch_date", required=True,
                        help="date of curation")
    parser.add_argument("-d", dest="done_filepath", required=True,
                        help="path to output file for terms that are done")
    parser.add_argument("-s", dest="skipped_filepath", required=True,
                        help="path to output file for terms that are skipped")
    parser.add_argument("-c", dest="comments_filepath", required=True,
                        help="path to output file for curator comments")
    parser.add_argument("-m", dest="import_filepath", required=True,
                        help="path to output markdown file for import mappings")
    parser.add_argument("-n", dest="new_output_filepath", required=False,
                        help="path to output markdown file for new mappings")
    args = parser.parse_args()
    export_table(args.input_filepath, args.batch_date, args.done_filepath, args.skipped_filepath,
                 args.comments_filepath, args.import_filepath)
    if args.new_input_filepath and args.new_output_filepath:
        export_new_terms(args.new_input_filepath, args.new_output_filepath)
