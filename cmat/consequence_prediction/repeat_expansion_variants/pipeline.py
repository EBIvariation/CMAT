#!/usr/bin/env python3
"""A pipeline to extract repeat expansion variants from ClinVar XML dump. For documentation refer to README.md"""

import logging
from collections import Counter

import numpy as np
import pandas as pd

from cmat import clinvar_xml_io
from cmat.clinvar_xml_io.repeat_variant import parse_all_identifiers, repeat_type_from_length
import cmat.consequence_prediction.common.biomart as biomart

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


STANDARD_CHROMOSOME_NAMES = {str(c) for c in range(1, 23)} | {'X', 'Y', 'M', 'MT'}


def none_to_nan(value):
    """Converts arguments which are None to np.nan, for consistency inside a Pandas dataframe."""
    return np.nan if value is None else value


def load_clinvar_data(clinvar_xml):
    """Load ClinVar data, preprocess, and return it as a Pandas dataframe."""
    # Iterate through ClinVar XML records
    variant_data = []  # To populate the return dataframe (see columns below)
    stats = Counter()
    for i, clinvar_record in enumerate(clinvar_xml_io.ClinVarDataset(clinvar_xml)):
        if i and i % 100000 == 0:
            total_repeat_expansion_variants = stats[clinvar_xml_io.ClinVarRecordMeasure.MS_REPEAT_EXPANSION] + \
                                              stats[clinvar_xml_io.ClinVarRecordMeasure.MS_NO_COMPLETE_COORDS]
            logger.info(f'Processed {i} records, collected {total_repeat_expansion_variants} repeat expansion variant '
                        f'candidates')

        # Skip a record if it does not contain variant information
        if not clinvar_record.measure:
            continue
        measure = clinvar_record.measure

        # Repeat expansion events come in two forms: with explicit coordinates and allele sequences (CHROM/POS/REF/ALT),
        # or without them. In the first case we can compute the explicit variant length as len(ALT) - len(REF). In the
        # second case, which is more rare but still important, we have to resort to parsing HGVS-like variant names.
        if measure.microsatellite_category:
            stats[measure.microsatellite_category] += 1
        # Skip the record if it's a deletion or a short insertion
        if not measure.is_repeat_expansion_variant:
            continue

        # Extract gene symbol(s). Here and below, dashes are sometimes assigned to be compatible with the variant
        # summary format which was used previously.
        gene_symbols = measure.preferred_gene_symbols
        if not gene_symbols:
            gene_symbols = ['-']

        # Extract HGNC ID
        hgnc_ids = measure.hgnc_ids
        hgnc_id = hgnc_ids[0] if len(hgnc_ids) == 1 and len(gene_symbols) == 1 else '-'

        repeat_type, transcript_id = parse_all_identifiers(measure)
        # If no identifier yields a repeat type, try to infer from elsewhere in the measure
        if not repeat_type and measure.explicit_insertion_length:
            repeat_type = repeat_type_from_length(measure.explicit_insertion_length)

        # Append data strings
        for gene_symbol in gene_symbols:
            variant_data.append([
                measure.preferred_or_other_name,
                clinvar_record.accession,
                gene_symbol,
                hgnc_id,
                none_to_nan(transcript_id),
                none_to_nan(repeat_type)
            ])
    total_repeat_expansion_variants = stats[clinvar_xml_io.ClinVarRecordMeasure.MS_REPEAT_EXPANSION] + \
                                      stats[clinvar_xml_io.ClinVarRecordMeasure.MS_NO_COMPLETE_COORDS]
    logger.info(f'Done. A total of {i} records, {total_repeat_expansion_variants} repeat expansion variant candidates')

    variants = pd.DataFrame(variant_data, columns=('Name',
                                                   'RCVaccession',
                                                   'GeneSymbol',
                                                   'HGNC_ID',
                                                   'TranscriptID',
                                                   'RepeatType'))

    # Since the same record can have coordinates in multiple builds, it can be repeated. Remove duplicates
    variants = variants.drop_duplicates()
    # Sort values by variant name
    return variants.sort_values(by=['Name']), stats


def annotate_ensembl_gene_info(variants, include_transcripts):
    """Annotate the `variants` dataframe with information about Ensembl gene ID and name"""

    # Ensembl gene ID can be determined using three ways, listed in the order of decreasing priority. Having multiple
    # ways is necessary because no single method works on all ClinVar variants.
    gene_annotation_sources = (
        # Dataframe column    Biomart column   Filtering function
        ('HGNC_ID',                 'hgnc_id', lambda i: i.startswith('HGNC:')),
        ('GeneSymbol',   'external_gene_name', lambda i: i != '-'),
        ('TranscriptID',        'refseq_mrna', lambda i: pd.notnull(i)),
    )
    query_columns = [('ensembl_gene_id', 'EnsemblGeneID')]
    if include_transcripts:
        query_columns.append(('ensembl_transcript_id', 'EnsemblTranscriptID'))

    # This copy of the dataframe is required to facilitate filling in data using the `combine_first()` method. This
    # allows us to apply priorities: e.g., if a gene ID was already populated using HGNC_ID, it will not be overwritten
    # by a gene ID determined using GeneSymbol.
    variants_original = variants.copy(deep=True)

    for column_name_in_dataframe, column_name_in_biomart, filtering_function in gene_annotation_sources:
        # Get all identifiers we want to query BioMart with
        identifiers_to_query = sorted({
            i for i in variants[column_name_in_dataframe]
            if filtering_function(i)
        })
        # Query BioMart for Ensembl Gene IDs
        annotation_info = biomart.query_biomart(
            key_column=(column_name_in_biomart, column_name_in_dataframe),
            query_columns=query_columns,
            identifier_list=identifiers_to_query,
        )
        # TODO collapse to list (?)

        # Make note where the annotations came from
        annotation_info['GeneAnnotationSource'] = column_name_in_dataframe
        # Combine the information we received with the *original* dataframe (a copy made before any iterations of this
        # cycle were allowed to run). This is similar to SQL merge.
        annotation_df = pd.merge(variants_original, annotation_info, on=column_name_in_dataframe, how='left')
        # Update main dataframe with the new values. This replaces the NaN values in the dataframe with the ones
        # available in another dataframe we just created, `annotation_df`.
        # TODO check this combine step if the previous info is not in lists
        variants = variants \
            .set_index([column_name_in_dataframe]) \
            .combine_first(annotation_df.set_index([column_name_in_dataframe]))

    # TODO check all this exploding stuff for transcripts
    # Reset index to default
    variants.reset_index(inplace=True)
    # Some records are being annotated to multiple Ensembl genes. For example, HGNC:10560 is being resolved to
    # ENSG00000285258 and ENSG00000163635. We need to explode dataframe by that column.
    variants = variants.explode('EnsemblGeneID')

    # TODO another query to biomart, this one should not need to change
    # Based on the Ensembl gene ID, annotate (1) gene name and (2) which chromosome it is on
    gene_query_columns = (
        ('external_gene_name', 'EnsemblGeneName'),
        ('chromosome_name', 'EnsemblChromosomeName'),
    )
    for column_name_in_biomart, column_name_in_dataframe in gene_query_columns:
        annotation_info = biomart.query_biomart(
            key_column=('ensembl_gene_id', 'EnsemblGeneID'),
            query_columns=[(column_name_in_biomart, column_name_in_dataframe)],
            identifier_list=sorted({str(i) for i in variants['EnsemblGeneID'] if str(i).startswith('ENSG')}),
        )
        variants = pd.merge(variants, annotation_info, on='EnsemblGeneID', how='left')
        # Check that there are no multiple mappings for any given ID
        assert variants[column_name_in_dataframe].str.len().dropna().max() == 1, \
            'Found multiple gene ID → gene attribute mappings!'
        # Convert the one-item list into a plain column
        variants = variants.explode(column_name_in_dataframe)

    return variants


def determine_complete(row):
    """Depending on the information, determine whether the record is complete, i.e., whether it has all necessary
        fields to be output for the final "consequences" table."""
    row['RecordIsComplete'] = (
        pd.notnull(row['EnsemblGeneID']) and
        pd.notnull(row['EnsemblGeneName']) and
        pd.notnull(row['RepeatType']) and
        row['EnsemblChromosomeName'] in STANDARD_CHROMOSOME_NAMES
    )
    return row


def generate_consequences_file(consequences, output_consequences):
    """Output final table."""

    if consequences.empty:
        logger.info('There are no records ready for output')
        return
    # Write the consequences table. This is used by the main evidence string generation pipeline.
    consequences.to_csv(output_consequences, sep='\t', index=False, header=False)
    # Output statistics
    logger.info(f'Generated {len(consequences)} consequences in total:')
    logger.info(f'  {sum(consequences.RepeatType == "trinucleotide_repeat_expansion")} trinucleotide repeat expansion')
    logger.info(f'  {sum(consequences.RepeatType == "short_tandem_repeat_expansion")} short tandem repeat expansion')


def extract_consequences(variants, include_transcripts):
    # Generate consequences table
    consequences = variants[variants['RecordIsComplete']] \
        .groupby(['RCVaccession', 'EnsemblGeneID', 'EnsemblGeneName'], group_keys=False)['RepeatType'] \
        .apply(set).reset_index(name='RepeatType')
    if consequences.empty:
        return consequences
    # Check that for every (RCV, gene) pair there is only one consequence type
    assert consequences['RepeatType'].str.len().dropna().max() == 1, 'Multiple (RCV, gene) → variant type mappings!'
    # Get rid of sets
    consequences['RepeatType'] = consequences['RepeatType'].apply(list)
    consequences = consequences.explode('RepeatType')
    # Form a four-column file compatible with the consequence mapping pipeline, for example:
    # RCV000005966    ENSG00000156475    PPP2R2B    trinucleotide_repeat_expansion
    consequences = consequences[['RCVaccession', 'EnsemblGeneID', 'EnsemblGeneName', 'RepeatType']]
    consequences.sort_values(by=['RepeatType', 'RCVaccession', 'EnsemblGeneID'], inplace=True)
    # Check that there are no empty cells in the final consequences table
    assert consequences.isnull().to_numpy().sum() == 0
    return consequences


def generate_all_variants_file(output_dataframe, variants):
    # Rearrange order of dataframe columns
    variants = variants[
        ['Name', 'RCVaccession', 'GeneSymbol', 'HGNC_ID', 'TranscriptID',
         'EnsemblGeneID', 'EnsemblGeneName', 'EnsemblChromosomeName', 'GeneAnnotationSource',
         'RepeatType', 'RecordIsComplete']
    ]
    # Write the full dataframe. This is used for debugging and investigation purposes.
    variants.sort_values(by=['Name', 'RCVaccession', 'GeneSymbol'])
    variants.to_csv(output_dataframe, sep='\t', index=False)


def main(clinvar_xml, include_transcripts, output_consequences=None, output_dataframe=None):
    """Process data and generate output files.

    Args:
        clinvar_xml: filepath to the ClinVar XML file.
        include_transcripts:
        output_consequences: filepath to the output file with variant consequences. The file uses a 6-column format
            compatible with the VEP mapping pipeline (see /consequence_prediction/README.md).
        output_dataframe: filepath to the output file with the full dataframe used in the analysis. This will contain
            all relevant columns and can be used for review or debugging purposes."""

    logger.info('Load and preprocess variant data')
    variants, s = load_clinvar_data(clinvar_xml)

    # Output ClinVar record statistics
    logger.info(f'''
        Microsatellite records: {sum(s.values())}
            With complete coordinates: {s[clinvar_xml_io.ClinVarRecordMeasure.MS_DELETION] +
                                        s[clinvar_xml_io.ClinVarRecordMeasure.MS_SHORT_EXPANSION] +
                                        s[clinvar_xml_io.ClinVarRecordMeasure.MS_REPEAT_EXPANSION]}
                Deletions: {s[clinvar_xml_io.ClinVarRecordMeasure.MS_DELETION]}
                Short insertions: {s[clinvar_xml_io.ClinVarRecordMeasure.MS_SHORT_EXPANSION]}
                Repeat expansions: {s[clinvar_xml_io.ClinVarRecordMeasure.MS_REPEAT_EXPANSION]}
            No complete coordinates: {s[clinvar_xml_io.ClinVarRecordMeasure.MS_NO_COMPLETE_COORDS]}
    '''.replace('\n' + ' ' * 8, '\n'))

    if variants.empty:
        logger.info('No variants to process')
        return None

    logger.info('Match each record to Ensembl gene ID and name')
    variants = annotate_ensembl_gene_info(variants, include_transcripts)

    logger.info('Determine variant type and whether the record is complete')
    variants = variants.apply(lambda row: determine_complete(row), axis=1)

    logger.info('Postprocess data and output the two final tables')
    if output_dataframe is not None:
        generate_all_variants_file(output_dataframe, variants)
    consequences = extract_consequences(variants, include_transcripts)
    if output_consequences is not None:
        generate_consequences_file(consequences, output_consequences)

    logger.info('Completed successfully')
    return consequences
