#!/usr/bin/env python3

import argparse
import logging

import pandas as pd

from cmat.output_generation.clinvar_to_evidence_strings import load_ontology_mapping
from cmat.trait_mapping.ols import get_replacement_term, is_current_and_in_ontology, OlsResult, \
    get_label_and_synonyms_from_ols, get_is_in_ontologies, MatchType, MappingSource, get_fields_with_match, \
    EXACT_SYNONYM_KEY

logger = logging.getLogger(__package__)


def previous_and_replacement_mappings(trait_name, previous_mappings, target_ontology, preferred_ontologies):
    if trait_name not in previous_mappings:
        yield '', ''
        return
    for uri, label in previous_mappings[trait_name]:
        label, match_type, mapping_source = get_mapping_attributes_from_ols(trait_name, uri, target_ontology, preferred_ontologies)
        trait_string = '|'.join([uri, label, str(match_type), mapping_source.to_string(target_ontology, preferred_ontologies)])
        replacement_string = ''
        if mapping_source == MappingSource.TARGET_OBSOLETE:
            replacement_string = find_replacement_mapping(trait_name, uri, target_ontology, preferred_ontologies)
        yield trait_string, replacement_string


def find_replacement_mapping(trait_name, previous_uri, ontology, preferred_ontologies, max_depth=1):
    replacement_uri = get_replacement_term(previous_uri, ontology)
    if not replacement_uri:
        return ''
    label, match_type, mapping_source = get_mapping_attributes_from_ols(trait_name, replacement_uri, ontology,
                                                                        preferred_ontologies)
    # If this term is also obsolete, try to find its replacement (at most max_depth times)
    if mapping_source == MappingSource.TARGET_OBSOLETE and replacement_uri.startswith('http') and max_depth > 0:
        return find_replacement_mapping(replacement_uri, ontology, preferred_ontologies, max_depth-1)
    trait_string = '|'.join([replacement_uri, label, str(match_type),
                             mapping_source.to_string(ontology, preferred_ontologies)])
    return trait_string


def find_exact_mappings(mappings):
    """Returns the top ranked exact label match and exact synonym match mappings."""
    exact_label_match_mapping = ''
    exact_synonym_match_mapping = ''
    for mapping in mappings:
        match_type = mapping.split('|')[2]
        if match_type == str(MatchType.EXACT_MATCH_LABEL) and exact_label_match_mapping == '':
            exact_label_match_mapping = mapping
        elif match_type == str(MatchType.EXACT_MATCH_SYNONYM) and exact_synonym_match_mapping == '':
            exact_synonym_match_mapping = mapping
    return exact_label_match_mapping, exact_synonym_match_mapping


def get_mapping_attributes_from_ols(trait_name, uri, target_ontology, preferred_ontologies):
    try:
        in_target_ontology, in_preferred_ontology = get_is_in_ontologies(uri, target_ontology, preferred_ontologies)
        is_current = is_current_and_in_ontology(uri, target_ontology) if in_target_ontology else False

        label, synonyms = get_label_and_synonyms_from_ols(uri)
        exact_match, contained_match, token_match = get_fields_with_match(trait_name, f'label,{EXACT_SYNONYM_KEY}',
                                                                          {'label': label, EXACT_SYNONYM_KEY: synonyms})

        ols_result = OlsResult(uri, label, None, exact_match, contained_match, token_match, in_target_ontology,
                               in_preferred_ontology, is_current)
        return label, ols_result.get_match_type(), ols_result.get_mapping_source()
    except Exception as e:
        logger.warning(f'Error while getting mapping attributes from OLS: {e}')
        return '', '', ''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--traits-for-curation',
        help='Table with traits for which the pipeline failed to make a confident prediction')
    parser.add_argument(
        '-m', '--previous-mappings',
        help='Table with all mappings previously issued by EVA. TSV with columns: ClinVar trait name; ontology URI; '
             'ontology label (not used)')
    parser.add_argument(
        '-c', '--previous-comments',
        help='Table with last round of curator comments. TSV with columns: ClinVar trait name; comments')
    parser.add_argument(
        '-p', '--preferred-ontologies', help='List of preferred ontologies to use', default='efo,hp,mondo')
    parser.add_argument(
        '-o', '--output',
        help='Output TSV to be loaded in Google Sheets for manual curation')
    args = parser.parse_args()

    # Load all previous mappings: ClinVar trait name to ontology URI
    previous_mappings, target_ontology = load_ontology_mapping(args.previous_mappings)

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
        # Use maximum of 50 mappings to improve Google Sheets performance
        mappings = fields[3:53]
        exact_match, exact_synonym_match = find_exact_mappings(mappings)
        for previous_mapping, replacement_mapping in previous_and_replacement_mappings(
                trait_name, previous_mappings, target_ontology, args.preferred_ontologies.split(',')):
            rows.append([trait_name, trait_freq, notes, previous_mapping, replacement_mapping,
                         exact_match, exact_synonym_match] + mappings)

    rows.sort(key=lambda x: (x[2], int(x[1])), reverse=True)
    with open(args.output, 'w') as outfile:
        for row in rows:
            out_line = '\t'.join(row) + '\n'
            outfile.write(out_line)
